import os
from flask import Flask, redirect, session, request, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
import yt_dlp
import razorpay
import hmac, hashlib

# App
app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-please-change")

# Config
BASE_URL = os.environ.get("BASE_URL")  # required
FRONTEND_URL = os.environ.get("FRONTEND_URL")  # required
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "rdsprojectsmyself@gmail.com")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

if not BASE_URL or not FRONTEND_URL:
    raise RuntimeError("BASE_URL and FRONTEND_URL env vars must be set")

# Cookies & CORS
app.config.update(
    SESSION_COOKIE_NAME="rds_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

CORS(app, supports_credentials=True, origins=[FRONTEND_URL])

# OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://openidconnect.googleapis.com/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

# DB utilities
from db import init_db, get_app_config, set_payments_enabled, create_payment, update_payment, get_stats, log_download
init_db()

# Razorpay client (if keys present)
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

@app.route("/")
def index():
    return "RDS Video Downloader Backend - healthy"

# Auth endpoints
@app.route("/api/auth/google")
def google_login():
    redirect_uri = f"{BASE_URL}/api/auth/google/callback"
    return google.authorize_redirect(redirect_uri)

@app.route("/api/auth/google/callback")
def google_callback():
    token = google.authorize_access_token()
    user = google.get('userinfo').json()
    session['user'] = {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "is_admin": user.get("email") == ADMIN_EMAIL,
        "is_paid": False
    }
    session.modified = True
    # redirect back to frontend dashboard with flag
    return redirect(f"{FRONTEND_URL}/dashboard.html?login=success")

@app.route("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"status":"ok"})

@app.route("/api/user/profile")
def profile():
    user = session.get("user")
    if not user:
        return jsonify({"error":"Not authenticated"}), 401
    # also send current payments_enabled
    cfg = get_app_config()
    payments_enabled = cfg.get("payments_enabled","false") == "true"
    user["payments_enabled"] = payments_enabled
    return jsonify(user)

# App config endpoint
@app.route("/api/app/config")
def app_config():
    cfg = get_app_config()
    return jsonify({k:v for k,v in cfg.items()})

# Admin toggle payments
@app.route("/api/admin/toggle-payments", methods=["POST"])
def toggle_payments():
    user = session.get("user")
    if not user or not user.get("is_admin"):
        return jsonify({"error":"unauthorized"}), 403
    data = request.json or {}
    enabled = bool(data.get("enabled"))
    set_payments_enabled(enabled)
    return jsonify({"payments_enabled": enabled})

# Video info endpoint (yt-dlp)
@app.route("/api/video/info", methods=["POST"])
def video_info():
    payload = request.json or {}
    url = payload.get("url")
    if not url:
        return jsonify({"error":"url required"}), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        formats = []
        for f in info.get("formats", []):
            formats.append({
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution"),
                "note": f.get("format_note")
            })
        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "platform": info.get("extractor"),
            "formats": formats[:12]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Video download endpoint (simulation, logs to DB)
@app.route("/api/video/download", methods=["POST"])
def video_download():
    data = request.json or {}
    user_id = session.get("user", {}).get("sub", "anonymous")
    log_download(user_id, data.get("platform","unknown"), data.get("url"), data.get("format"), data.get("quality"))
    return jsonify({"status":"started","message":"Download started (simulation)"})

# Admin stats
@app.route("/api/admin/stats")
def admin_stats():
    user = session.get("user")
    if not user or not user.get("is_admin"):
        return jsonify({"error":"unauthorized"}), 403
    return jsonify(get_stats())

# Create order (Razorpay) - checks payments_enabled
@app.route("/api/create-order", methods=["POST"])
def create_order():
    user = session.get("user")
    if not user:
        return jsonify({"error":"Login required"}), 401
    cfg = get_app_config()
    if cfg.get("payments_enabled","false") != "true":
        return jsonify({"error":"payments disabled by admin"}), 403
    if not razorpay_client:
        return jsonify({"error":"razorpay not configured"}), 500

    amount = 4900  # ₹49.00 in paise
    order = razorpay_client.order.create({"amount": amount, "currency": "INR", "payment_capture": 1, "notes": {"email": user.get("email")}})
    create_payment(user.get("sub"), order.get("id"), amount)
    return jsonify({
        "order_id": order.get("id"),
        "amount": amount,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "name": user.get("name"),
        "email": user.get("email")
    })

# Verify payment
@app.route("/api/verify-payment", methods=["POST"])
def verify_payment():
    data = request.json or {}
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    # compute signature
    msg = f"{order_id}|{payment_id}"
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        update_payment(order_id, payment_id, "failed")
        return jsonify({"error":"invalid signature"}), 400
    update_payment(order_id, payment_id, "captured")
    # mark user is_paid in session
    if 'user' in session:
        session['user']['is_paid'] = True
    return jsonify({"status":"success"})

# Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    # allow HTTP locally for dev testing
    if os.environ.get("FLASK_ENV") == "development":
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(host="0.0.0.0", port=port)


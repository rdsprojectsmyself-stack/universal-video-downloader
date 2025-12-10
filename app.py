import os
from flask import Flask, redirect, session, request, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
import yt_dlp

# -------------------------------------------------
# App Setup
# -------------------------------------------------
app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-prod")

# ✅ COOKIE CONFIG (CRITICAL)
app.config.update(
    SESSION_COOKIE_NAME="rds_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",   # ✅ required for cross-site
    SESSION_COOKIE_SECURE=True,       # ✅ HTTPS only (Render)
)

# ✅ CORS (Frontend domain only)
CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://rdsvideodownloader.unaux.com",
    ],
)

# -------------------------------------------------
# Environment Variables
# -------------------------------------------------
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
BASE_URL = os.environ.get("BASE_URL")
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://rdsvideodownloader.unaux.com"
)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "rdsprojectsmyself@gmail.com")

if not BASE_URL:
    raise RuntimeError("BASE_URL env variable is REQUIRED")

# -------------------------------------------------
# OAuth Setup
# -------------------------------------------------
oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    client_kwargs={
        "scope": "openid email profile"
    },
)

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def home():
    return "✅ RDS Video Downloader Backend Running"

# ---------------- AUTH ----------------
@app.route("/api/auth/google")
def google_login():
    redirect_uri = f"{BASE_URL}/api/auth/google/callback"
    return google.authorize_redirect(redirect_uri)

@app.route("/api/auth/google/callback")
def google_callback():
    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    session["user"] = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "is_admin": user_info.get("email") == ADMIN_EMAIL,
    }

    session.modified = True

    # ✅ Redirect back to frontend
    return redirect(f"{FRONTEND_URL}/dashboard.html?login=success")

@app.route("/api/user/profile")
def user_profile():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user)

@app.route("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"status": "logged_out"})

# ---------------- VIDEO INFO ----------------
@app.route("/api/video/info", methods=["POST"])
def get_video_info():
    data = request.json or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = [
            {
                "format_id": f["format_id"],
                "ext": f.get("ext"),
                "resolution": f.get("resolution"),
            }
            for f in info.get("formats", [])
            if f.get("vcodec") != "none"
        ]

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "platform": info.get("extractor"),
            "formats": formats[:6],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- ADMIN ----------------
@app.route("/api/admin/stats")
def admin_stats():
    user = session.get("user")
    if not user or not user.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    from db import get_stats
    return jsonify(get_stats())

# -------------------------------------------------
# Main
# -------------------------------------------------
if __name__ == "__main__":
    from db import init_db

    init_db()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

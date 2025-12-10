import os
from flask import Flask, redirect, session, request, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth

# -------------------------------------------------
# App Setup
# -------------------------------------------------
app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://rdsvideodownloader.unaux.com"
    ],
)

# -------------------------------------------------
# Environment Variables
# -------------------------------------------------
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "rdsprojectsmyself@gmail.com")
BASE_URL = os.environ.get("BASE_URL")  # NO FALLBACK

if not BASE_URL:
    raise RuntimeError("BASE_URL must be set")

# -------------------------------------------------
# OAuth Setup
# -------------------------------------------------
oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://accounts.google.com/o/oauth2/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    client_kwargs={"scope": "openid email profile"},
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
    user = google.get("userinfo").json()

    session["user"] = {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
    }

    return redirect("https://rdsvideodownloader.unaux.com/dashboard")

@app.route("/api/user/profile")
def user_profile():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user)

# ---------------- VIDEO INFO ----------------
import yt_dlp

@app.route("/api/video/info", methods=["POST"])
def get_video_info():
    url = request.json.get("url")
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
    if not user or user["email"] != ADMIN_EMAIL:
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

    if os.environ.get("FLASK_ENV") == "development":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    app.run(host="0.0.0.0", port=port)

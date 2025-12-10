import os
import json
from flask import Flask, redirect, url_for, session, request, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Configuration from environment variables
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'rdsprojectsmyself@gmail.com')

# OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

@app.route('/')
def home():
    return "RDS Video Downloader Backend Running"

@app.route('/api/auth/google')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def authorize():
    token = google.authorize_access_token()
    user_info = google.parse_id_token(token)
    session['user'] = user_info
    # In production, you would redirect to the frontend here
    return jsonify(user_info)

@app.route('/api/user/profile')
def profile():
    user = session.get('user')
    if user:
        return jsonify(user)
    return jsonify({"error": "Not authenticated"}), 401

    # For local testing, allow HTTP
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True, port=5000)

# Initialize DB
# Initialize DB
from db import init_db, add_user, log_download, get_stats, create_payment, update_payment, get_user_status
init_db()

import yt_dlp

@app.route('/api/video/info', methods=['POST'])
def get_video_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Simple platform detection
            platform = info.get('extractor', 'unknown')
            
            formats = []
            # Simplified format processing (in reality complex)
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'resolution': f.get('resolution'),
                        'note': f.get('format_note')
                    })
            
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'platform': platform,
                'formats': formats[:6], # Limit as requested
                'raw_formats': formats # For advanced use
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/download', methods=['POST'])
def download_video():
    # Placeholder for actual download logic
    # Real implementation needs task queue (Celery/RQ) for large files
    # Here we just log and simulate
    data = request.json
    user_id = session.get('user', {}).get('sub', 'anonymous')
    
    log_download(
        user_id=user_id,
        platform=data.get('platform', 'unknown'),
        video_url=data.get('url'),
        fmt=data.get('format'),
        quality=data.get('quality')
    )
    
    # In a real app, you'd stream the file content here using send_file
    # or return a signed URL to the file if stored in cloud
    return jsonify({'status': 'started', 'message': 'Download started (simulation)'})

@app.route('/api/audio/trim', methods=['POST'])
def trim_audio():
    # Placeholder for audio trimming using ffmpeg
    # Would require downloading the file first, then running ffmpeg
    data = request.json
    # start_time, end_time, url/file_id
    
    return jsonify({'status': 'started', 'message': 'Audio trimming started (simulation)'})

@app.route('/api/admin/stats')
def admin_stats():
    # Verify admin email
    user = session.get('user')
    if not user or user.get('email') != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    stats = get_stats()
    return jsonify(stats)

# --- Razorpay Integration ---
import razorpay
import hmac
import hashlib

# These should be in env vars. Using placeholders for testing if env not set.
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_PLACEHOLDER')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'secret_PLACEHOLDER')

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route('/api/create-order', methods=['POST'])
def create_order():
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Login required'}), 401
        
    try:
        amount = 4900 # 49.00 INR (Amount in paise)
        currency = 'INR'
        
        order_data = {
            'amount': amount,
            'currency': currency,
            'payment_capture': 1, # Auto capture
            'notes': {
                'user_email': user['email']
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        # Log payment attempt
        create_payment(
            user_id=user['sub'], 
            order_id=order['id'], 
            amount=amount
        )
        
        return jsonify({
            'order_id': order['id'],
            'amount': amount,
            'currency': currency,
            'key_id': RAZORPAY_KEY_ID,
            'name': user.get('name'),
            'email': user.get('email')
        })
    except Exception as e:
        print(f"Razorpay Error: {e}")
        return jsonify({'error': 'Failed to create order. Ensure Razorpay keys are set.'}), 500

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    data = request.json
    
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    # Signature Verification
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id
    }
    
    try:
        # Re-construct signature
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            key=RAZORPAY_KEY_SECRET.encode('utf-8'),
            msg=msg.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(generated_signature, razorpay_signature):
            # Payment Successful
            update_payment(razorpay_order_id, razorpay_payment_id, 'captured')
            # User session paid update (optional, usually re-fetch from DB)
            if 'user' in session:
                session['user']['is_paid'] = True
                
            return jsonify({'status': 'success', 'message': 'Payment verified and Premium activated'})
        else:
            update_payment(razorpay_order_id, razorpay_payment_id, 'failed')
            return jsonify({'error': 'Invalid signature'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Update auth callback to check payment status
    @app.after_request
    def add_header(response):
        return response
        
    init_db()
    # For local testing, allow HTTP
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True, port=5000)

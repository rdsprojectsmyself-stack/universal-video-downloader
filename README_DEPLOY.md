RDS Video Backend - Deploy Notes
--------------------------------

Environment variables (set in Render or .env):
- ADMIN_EMAIL=rdsprojectsmyself@gmail.com
- BASE_URL=https://universal-video-downloader-ei3v.onrender.com
- FRONTEND_URL=https://rdsvideodownloader.unaux.com
- GOOGLE_CLIENT_ID=...
- GOOGLE_CLIENT_SECRET=...
- GOOGLE_REDIRECT_URI=${BASE_URL}/auth/google/callback
- RAZORPAY_KEY_ID=...
- RAZORPAY_KEY_SECRET=...
- SESSION_SECRET=supersecret
- NODE_ENV=production

Quick deploy (Render):
1. Push this repo to GitHub.
2. Create a Web Service on Render (Node).
3. Use npm install (render auto) and npm start.
4. Add env vars on Render dashboard per above.
5. Ensure Google OAuth redirect in Google Console matches ${BASE_URL}/auth/google/callback.

Notes on yt-dlp:
- Dockerfile installs yt-dlp and ffmpeg to support youtube-dl/yt-dlp operations.
- For heavy loads use queued worker / S3 offload.

Security:
- Replace in-memory demo storage with database (Postgres/Mongo) for production.
- Use HTTPS (Render provides it).
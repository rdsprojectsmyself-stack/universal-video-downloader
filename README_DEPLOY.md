RDS Backend - Render deployment instructions (Node.js)

This package is prepared to deploy on Render as a Node web service (no Docker).

Steps to deploy:
1. Push this repository to GitHub.
2. In Render, create a new **Web Service** and choose the Git repo & branch.
3. Select **Environment: Node** (Render will auto-detect).
4. Build command: `npm install`
5. Start command: `npm start`
6. Add the environment variables shown in `.env.example` via Render dashboard (Environment -> Add Environment Variable).
7. Deploy. The server will listen on the port Render provides via the PORT environment variable.

Notes:
- This package intentionally does not install yt-dlp or ffmpeg. For production, install yt-dlp (pip) or bundle a static ffmpeg binary depending on your deployment choice.
- Endpoints included:
  - GET  /api/app/config        -> returns a small config object
  - POST /api/video/info        -> returns metadata for a given url using yt-dlp (if available)
  - POST /api/video/download    -> attempts to stream/download using yt-dlp (basic)
  - GET  /auth/profile          -> returns session user (if any)
  - GET  /auth/google           -> placeholder for Google OAuth (will redirect if configured)
  - GET  /auth/logout           -> clears session
  - Admin & payment endpoints are present as safe placeholders.
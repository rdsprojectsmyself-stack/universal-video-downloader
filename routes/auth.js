const express = require('express');
const router = express.Router();

// GET /auth/profile
router.get('/profile', (req, res) => {
  if (req.session && req.session.user) {
    return res.json(req.session.user);
  }
  return res.status(401).json({ error: 'Not logged in' });
});

// GET /auth/google - placeholder redirect or 501 if not configured
router.get('/google', (req, res) => {
  const client = process.env.GOOGLE_CLIENT_ID;
  const redirect = process.env.GOOGLE_REDIRECT_URI;
  if (!client || !redirect) {
    return res.status(501).send('Google OAuth not configured on server. Please set GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI.');
  }
  // Minimal OAuth redirect to Google's consent screen (PKCE not implemented here)
  const scope = encodeURIComponent('profile email');
  const redirectUri = encodeURIComponent(redirect);
  const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${client}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}&access_type=online`;
  return res.redirect(url);
});

// GET /auth/logout
router.get('/logout', (req, res) => {
  req.session.destroy(() => res.json({ ok: true }));
});

module.exports = router;
import express from 'express';
import passport from 'passport';
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';

const router = express.Router();

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5500';

passport.serializeUser((user, done) => done(null, user));
passport.deserializeUser((obj, done) => done(null, obj));

passport.use(new GoogleStrategy({
  clientID: GOOGLE_CLIENT_ID,
  clientSecret: GOOGLE_CLIENT_SECRET,
  callbackURL: `${BASE_URL}/auth/google/callback`
}, (accessToken, refreshToken, profile, done) => {
  const user = {
    id: profile.id,
    name: profile.displayName,
    email: profile.emails?.[0]?.value,
    picture: profile.photos?.[0]?.value,
    is_admin: profile.emails?.[0]?.value === process.env.ADMIN_EMAIL,
    is_paid: false
  };
  done(null, user);
}));

// start oauth
router.get('/google', passport.authenticate('google', { scope: ['profile','email'] }));

router.get('/google/callback', passport.authenticate('google', { failureRedirect: `${FRONTEND_URL}/index.html?login=failed`, session: true }), (req, res) => {
  res.redirect(`${FRONTEND_URL}/downloader.html`);
});

router.get('/logout', (req, res) => {
  req.logout(err => {
    res.clearCookie('connect.sid');
    res.redirect(process.env.FRONTEND_URL || '/');
  });
});

// profile for frontend (used by Scripts.js)
router.get('/profile', (req, res) => {
  if (req.user) return res.json(req.user);
  res.status(401).json({ error: 'Not logged in' });
});

export default router;
import express from 'express';
const router = express.Router();

let APP_CONFIG = { payments_enabled: false };

function requireAdmin(req, res, next) {
  if (req.user && req.user.is_admin) return next();
  return res.status(403).json({ error: 'Admin required' });
}

router.get('/stats', requireAdmin, (req, res) => {
  res.json({
    total_downloads: 12345,
    active_users: 321,
    platform_usage: { youtube: 70, instagram: 15, facebook: 10, other: 5 },
    payments_enabled: APP_CONFIG.payments_enabled
  });
});

router.post('/settings/payments', requireAdmin, (req, res) => {
  APP_CONFIG.payments_enabled = !!req.body.payments_enabled;
  res.json({ payments_enabled: APP_CONFIG.payments_enabled });
});

// expose user profile under /api/user/profile for frontend compatibility
router.get('/user/profile', (req, res) => {
  if (req.user) return res.json(req.user);
  res.status(401).json({ error: 'Not logged in' });
});

export default router;
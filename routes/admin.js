const express = require('express');
const router = express.Router();

// GET /api/admin/stats - placeholder stats
router.get('/stats', (req, res) => {
  res.json({
    total_downloads: 0,
    active_users: 0,
    payments_enabled: false,
    platform_usage: { youtube: 0, vimeo: 0, instagram: 0 }
  });
});

module.exports = router;
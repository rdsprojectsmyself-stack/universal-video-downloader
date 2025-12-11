const express = require('express');
const router = express.Router();

// Dummy payment endpoints (implement Razorpay server-side flow here)
router.post('/create-order', (req, res) => {
  return res.json({ order_id: 'test_order_1', amount: 10000, key: process.env.RAZORPAY_KEY || '' });
});

router.post('/verify', (req, res) => {
  // In real app, verify signature and mark user as paid
  return res.json({ status: 'success' });
});

module.exports = router;
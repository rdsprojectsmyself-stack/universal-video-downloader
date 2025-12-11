import express from 'express';
import Razorpay from 'razorpay';
import crypto from 'crypto';

const router = express.Router();
const razor = new Razorpay({ key_id: process.env.RAZORPAY_KEY_ID || '', key_secret: process.env.RAZORPAY_KEY_SECRET || '' });

router.post('/create-order', async (req, res) => {
  try {
    const amount = 49900; // paise
    const receipt = `rcpt_${Date.now()}`;
    const order = await razor.orders.create({ amount, currency: 'INR', receipt });
    res.json({ order_id: order.id, amount: order.amount, currency: order.currency, key: process.env.RAZORPAY_KEY_ID });
  } catch (e) {
    console.error('razor create error', e);
    res.status(500).json({ error: 'Payment creation failed' });
  }
});

router.post('/verify', async (req, res) => {
  try {
    const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = req.body;
    const body = razorpay_order_id + '|' + razorpay_payment_id;
    const expected = crypto.createHmac('sha256', process.env.RAZORPAY_KEY_SECRET || '').update(body).digest('hex');
    if (expected === razorpay_signature) {
      if (req.user) req.user.is_paid = true;
      return res.json({ status: 'success' });
    }
    return res.json({ status: 'failure' });
  } catch (e) {
    console.error('verify error', e);
    res.status(500).json({ error: 'Verification failed' });
  }
});

export default router;
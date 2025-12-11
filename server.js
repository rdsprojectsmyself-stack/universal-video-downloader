/**
 * server.js - Simple Express backend for RDS Video Downloader
 * Render-ready (Node), minimal dependencies, no Dockerfile included.
 */

const express = require('express');
const session = require('express-session');
const cookieParser = require('cookie-parser');
const bodyParser = require('body-parser');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 10000;

app.use(cors({
  origin: process.env.FRONTEND_URL || true,
  credentials: true,
}));
app.use(cookieParser());
app.use(bodyParser.json({ limit: '5mb' }));
app.use(bodyParser.urlencoded({ extended: true }));

app.use(session({
  secret: process.env.SECRET_KEY || 'dev-secret',
  resave: false,
  saveUninitialized: true,
  cookie: { secure: false }
}));

// Simple health/config
app.get('/api/app/config', (req, res) => {
  res.json({ payments_enabled: false });
});

// Attach routes
app.use('/api/video', require('./routes/video'));
app.use('/api/admin', require('./routes/admin'));
app.use('/api/payment', require('./routes/payment'));

// Auth routes (non-/api because frontend used /auth/...)
app.use('/auth', require('./routes/auth'));

// Serve static if needed (not required for Render separate frontend)
// app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req,res) => res.send('RDS Backend is running'));

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
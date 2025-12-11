const express = require('express');
const { spawn } = require('child_process');
const router = express.Router();

// POST /api/video/info
// Expects JSON { url: "https://..." }
router.post('/info', async (req, res) => {
  const url = req.body?.url || req.query?.url;
  if (!url) return res.status(400).json({ error: 'Missing url' });

  // Try to run yt-dlp -J url to get metadata as JSON
  try {
    const proc = spawn('yt-dlp', ['-J', url]);
    let out = '';
    let err = '';

    proc.stdout.on('data', (c) => out += c.toString());
    proc.stderr.on('data', (c) => err += c.toString());

    proc.on('close', (code) => {
      if (code !== 0) {
        return res.status(500).json({ error: 'yt-dlp failed', detail: err });
      }
      try {
        const info = JSON.parse(out);
        // Normalize minimal response
        const formats = (info.formats || []).map(f => ({
          itag: f.format_id || f.itag,
          ext: f.ext,
          mime: f.acodec ? `audio/${f.acodec}` : f.vcodec ? `video/${f.vcodec}` : f.mime || '',
          quality: f.format_note || f.height || '',
        }));
        return res.json({ title: info.title, thumbnail: info.thumbnail, duration: info.duration, formats });
      } catch (e) {
        return res.status(500).json({ error: 'Parsing yt-dlp output failed', detail: e.message });
      }
    });
  } catch (e) {
    return res.status(500).json({ error: 'yt-dlp not available on server', detail: e.message });
  }
});

// POST /api/video/download
// Basic: returns a redirect URL or proxy - here we attempt to stream via yt-dlp to stdout if available
router.post('/download', async (req, res) => {
  const { url, itag, format, quality } = req.body || {};
  if (!url) return res.status(400).json({ error: 'Missing url' });

  // Build yt-dlp args - this is simplified; consider security & validation
  const args = ['-o', '-', url, '--no-playlist', '--rm-cache-dir'];
  if (itag) args.push('-f', String(itag));
  // Stream to stdout then pipe to response
  try {
    const proc = spawn('yt-dlp', args, { stdio: ['ignore', 'pipe', 'pipe'] });
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', 'attachment; filename="download"');
    proc.stdout.pipe(res);
    proc.stderr.on('data', d => console.error('yt-dlp:', d.toString()));
    proc.on('close', () => res.end());
  } catch (e) {
    res.status(500).json({ error: 'Download failed', detail: e.message });
  }
});

module.exports = router;
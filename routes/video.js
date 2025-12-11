import express from 'express';
import { infoForUrl, streamForUrl } from '../utils/yt.js';

const router = express.Router();

router.post('/info', async (req, res) => {
  const url = req.body?.url || req.query?.url;
  if (!url) return res.status(400).json({ error: 'Missing url' });
  try {
    const info = await infoForUrl(url);
    const formats = (info.formats || []).map(f => ({
      itag: f.format_id || f.itag,
      ext: f.ext,
      mime: f.acodec || f.vcodec ? `${f.vcodec || ''}/${f.acodec || ''}` : f.mime,
      quality: f.quality || f.format_note || f.height || '',
      resolution: f.format_note || f.height || ''
    }));
    res.json({ title: info.title, thumbnail: info.thumbnail, duration: info.duration, formats });
  } catch (e) {
    console.error('info error', e);
    res.status(500).json({ error: e.message || 'Failed to fetch info' });
  }
});

router.post('/download', async (req, res) => {
  const { url, itag } = req.body || req.query;
  if (!url) return res.status(400).json({ error: 'Missing url' });
  try {
    const stream = await streamForUrl(url, { itag });
    const filename = `rds-download-${Date.now()}.mp4`;
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Type', 'application/octet-stream');
    stream.pipe(res);
  } catch (e) {
    console.error('download error', e);
    res.status(500).json({ error: e.message || 'Download failed' });
  }
});

export default router;
/**
 * Small utility wrapper for yt-dlp execution if you want to import.
 * Note: This module expects 'yt-dlp' to be installed on the server host.
 */
const { spawn } = require('child_process');

function infoForUrl(url) {
  return new Promise((resolve, reject) => {
    try {
      const proc = spawn('yt-dlp', ['-J', url]);
      let out = '', err = '';
      proc.stdout.on('data', c => out += c.toString());
      proc.stderr.on('data', c => err += c.toString());
      proc.on('close', (code) => {
        if (code !== 0) return reject(new Error(err || 'yt-dlp failed'));
        try { resolve(JSON.parse(out)); } catch (e) { reject(e); }
      });
    } catch (e) { reject(e); }
  });
}

module.exports = { infoForUrl };
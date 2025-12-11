import youtubedl from 'youtube-dl-exec';
import { PassThrough } from 'stream';

export async function infoForUrl(url) {
  const info = await youtubedl(url, {
    dumpSingleJson: true,
    noWarnings: true,
    noCheckCertificate: true,
    preferFreeFormats: true,
    youtubeSkipDashManifest: true,
  });
  return info;
}

export async function streamForUrl(url, opts = {}) {
  const args = [
    url,
    '--no-warnings',
    '--no-check-certificate',
    '-f', opts.itag ? String(opts.itag) : 'best',
    '-o', '-'
  ];
  const subprocess = youtubedl.raw(args);
  const pass = new PassThrough();
  subprocess.stdout.pipe(pass);
  subprocess.stderr.on('data', chunk => console.error('yt-dlp:', chunk.toString()));
  subprocess.on('close', code => console.log('yt-dlp closed', code));
  return pass;
}
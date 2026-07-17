// Generates the display renditions of the two frames. Never upscales.
// Source of truth is website-rebuild/assets. Output goes to public/images.
import sharp from 'sharp';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(here, '../../assets');
const out = path.resolve(here, '../public/images');
await mkdir(path.join(out, 'logos'), { recursive: true });

const frames = [
  // Portrait capped at its true 2048px until the original file is sourced.
  { name: 'jd-portrait', widths: [768, 1280, 2048] },
  { name: 'jd-speaking', widths: [640, 960, 1262] },
];

for (const frame of frames) {
  const input = path.join(src, `${frame.name}.jpg`);
  const meta = await sharp(input).metadata();
  for (const w of frame.widths) {
    if (w > meta.width) {
      throw new Error(`${frame.name}: ${w}px exceeds source width ${meta.width}px. No upscaling.`);
    }
    await sharp(input)
      .resize({ width: w })
      .jpeg({ quality: 82, mozjpeg: true })
      .toFile(path.join(out, `${frame.name}-${w}.jpg`));
    await sharp(input)
      .resize({ width: w })
      .webp({ quality: 80 })
      .toFile(path.join(out, `${frame.name}-${w}.webp`));
  }
  console.log(`${frame.name}: ${frame.widths.join(', ')}px done`);
}

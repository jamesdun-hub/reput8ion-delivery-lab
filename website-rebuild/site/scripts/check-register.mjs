// The launch gate. Run against the built site: npm run build && npm run check.
// Fails on anything the brief bans in any shipped string, and on any
// placeholder or sample content still present. Deploy blocks until clean.
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, '../dist');
const samples = JSON.parse(
  await readFile(path.resolve(here, '../src/data/samples.json'), 'utf8')
);

const BANNED_PHRASES = [
  'comprehensive communications support',
  'tailored solutions',
  'we partner with organisations to',
  'leveraging our experience',
  'best-in-class',
  'world-class',
  'sector-leading',
  'our team of experts',
  'we are passionate about',
  'proactive strategic communications',
  'in today’s competitive landscape',
  "in today's competitive landscape",
  'unlock',
  'reach out',
  'bespoke to the situation',
  'trusted adviser',
  'insights',
];

const US_SPELLINGS = [
  /\borganizations?\b/i,
  /\banalyze\b/i,
  /\bcolor\b/i,
  /\bcenter\b/i,
  /\bprogram\b(?!me)/i,
  /\bfavor\b/i,
  /\blicense\b/i,
  /\bdefense\b/i,
];

async function htmlFiles(dir) {
  const found = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) found.push(...(await htmlFiles(full)));
    else if (entry.name.endsWith('.html')) found.push(full);
  }
  return found;
}

// Visible text plus alt and meta content values. Styles and scripts excluded.
function extractText(html) {
  const attrs = [...html.matchAll(/(?:alt|content)="([^"]*)"/g)].map((m) => m[1]);
  const body = html
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(/<script[\s\S]*?<\/script>/g, ' ')
    .replace(/<[^>]+>/g, ' ');
  return `${body} ${attrs.join(' ')}`;
}

const failures = [];
const files = await htmlFiles(dist);
if (files.length === 0) failures.push('No built HTML found. Run the build first.');

let photoCount = 0;

for (const file of files) {
  const rel = path.relative(dist, file);
  const html = await readFile(file, 'utf8');
  const text = extractText(html);

  if (html.includes('data-placeholder')) {
    failures.push(`${rel}: placeholder content still present`);
  }
  if (text.includes('—')) {
    failures.push(`${rel}: em dash in shipped text`);
  }
  for (const phrase of BANNED_PHRASES) {
    if (text.toLowerCase().includes(phrase.toLowerCase())) {
      failures.push(`${rel}: banned phrase "${phrase}"`);
    }
  }
  for (const re of US_SPELLINGS) {
    const hit = text.match(re);
    if (hit) failures.push(`${rel}: US spelling "${hit[0]}"`);
  }

  // Exactly two photographs on the whole site. Logos are exempt.
  for (const m of html.matchAll(/<img[^>]+src="([^"]+)"/g)) {
    if (m[1].startsWith('/images/jd-')) photoCount += 1;
  }
}

const sampleCount = samples.notes.length + samples.problems.length;
if (sampleCount > 0) {
  failures.push(
    `samples.json lists ${sampleCount} sample entries not yet replaced or approved`
  );
}

const distinctPhotos = new Set();
for (const file of files) {
  const html = await readFile(file, 'utf8');
  for (const m of html.matchAll(/\/images\/(jd-[a-z]+)-\d+\.(?:jpg|webp)/g)) {
    distinctPhotos.add(m[1]);
  }
}
if (distinctPhotos.size > 2) {
  failures.push(`More than two photographs in the build: ${[...distinctPhotos].join(', ')}`);
}

if (failures.length) {
  console.error(`Launch gate failed with ${failures.length} finding(s):\n`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(`Launch gate clean across ${files.length} pages.`);

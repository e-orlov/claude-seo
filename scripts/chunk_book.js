const fs = require('fs');

const inputPath = process.argv[2] || 'knowledge/art-of-seo.txt';
const outputPath = process.argv[3] || 'knowledge/art-of-seo-chunks.json';

const text = fs.readFileSync(inputPath, 'utf8');
const lines = text.split('\n');

const chapterMap = {
  60:   'Chapter 1: Search Fundamentals & User Intent',
  736:  'Chapter 2: Search Fundamentals',
  1702: 'Chapter 3: SEO Toolbox',
  2578: 'Chapter 4: SEO Planning',
  3330: 'Chapter 5: Keyword Research',
  4633: 'Chapter 6: SEO Analytics and Measurement',
  5184: 'Chapter 7: Google Algorithm Updates and Penalties',
  6705: 'Chapter 8: Auditing and Troubleshooting',
  8506: 'Chapter 9: Promoting Your Site and Link Building',
};

const chapterStarts = Object.keys(chapterMap).map(Number).sort((a, b) => a - b);

function getChapter(lineNum) {
  let chapter = 'Preface';
  for (const start of chapterStarts) {
    if (lineNum >= start) chapter = chapterMap[start];
  }
  return chapter;
}

const TARGET_WORDS = 350;
const MAX_WORDS = 500;

const rawChunks = [];
let buf = [];
let bufWords = 0;
let currentChapter = 'Preface';
let chunkStart = 0;

function flush(endLine) {
  const t = buf.join('\n').trim();
  if (t.split(/\s+/).filter(Boolean).length < 50) { buf = []; bufWords = 0; chunkStart = endLine + 1; return; }
  rawChunks.push({ chapter: currentChapter, line_start: chunkStart, line_end: endLine, text: t });
  buf = [];
  bufWords = 0;
  chunkStart = endLine + 1;
}

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  const chapter = getChapter(i);

  if (chapter !== currentChapter) {
    flush(i - 1);
    currentChapter = chapter;
    chunkStart = i;
  }

  buf.push(line);
  bufWords += line.split(/\s+/).filter(Boolean).length;

  const isBlank = line.trim() === '';
  const prevIsBlank = buf.length > 1 && buf[buf.length - 2].trim() === '';

  // Flush at paragraph break when over target
  if (isBlank && bufWords >= TARGET_WORDS) {
    flush(i);
    continue;
  }

  // Hard flush when way over max (no paragraph in sight)
  if (bufWords >= MAX_WORDS && isBlank) {
    flush(i);
  }
}
flush(lines.length - 1);

// Post-process: split oversized chunks by sentences
function splitLarge(chunk, maxWords) {
  if (chunk.text.split(/\s+/).length <= maxWords) return [chunk];

  const sentences = chunk.text.match(/[^.!?]+[.!?]+\s*/g) || [chunk.text];
  const parts = [];
  let cur = '';
  let curWords = 0;

  for (const sent of sentences) {
    const sw = sent.split(/\s+/).filter(Boolean).length;
    if (curWords + sw > maxWords && cur.trim()) {
      parts.push(cur.trim());
      cur = sent;
      curWords = sw;
    } else {
      cur += sent;
      curWords += sw;
    }
  }
  if (cur.trim()) parts.push(cur.trim());

  return parts.map(t => ({ ...chunk, text: t }));
}

const chunks = [];
for (const rc of rawChunks) {
  const sub = splitLarge(rc, MAX_WORDS);
  for (const s of sub) {
    chunks.push({ id: chunks.length + 1, ...s, word_count: s.text.split(/\s+/).filter(Boolean).length });
  }
}

fs.writeFileSync(outputPath, JSON.stringify(chunks, null, 2), 'utf8');

console.log(`Chunks created: ${chunks.length}`);
const min = Math.min(...chunks.map(c => c.word_count));
const max = Math.max(...chunks.map(c => c.word_count));
const avg = Math.round(chunks.reduce((s, c) => s + c.word_count, 0) / chunks.length);
console.log(`Word count — min: ${min}, avg: ${avg}, max: ${max}`);

const byChapter = {};
for (const c of chunks) byChapter[c.chapter] = (byChapter[c.chapter] || 0) + 1;
for (const [ch, count] of Object.entries(byChapter)) {
  console.log(`  ${count.toString().padStart(3)} chunks  ${ch}`);
}

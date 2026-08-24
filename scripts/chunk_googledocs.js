const fs = require('fs');
const path = require('path');

const argv = process.argv.slice(2);
const outIdx = argv.indexOf('--out');
const outputDir = outIdx !== -1 ? argv[outIdx + 1] : 'knowledge/googledocs-chunks';
const inputFiles = argv.filter((a, i) => a !== '--out' && (outIdx === -1 || i !== outIdx + 1));

if (!inputFiles.length) {
  console.error('Usage: node chunk_googledocs.js <file1.csv> [file2.csv ...] [--out <dir>]');
  process.exit(1);
}
fs.mkdirSync(outputDir, { recursive: true });

// --- RFC 4180 CSV parser ---
function parseCSV(text) {
  const rows = [];
  let i = 0;
  const n = text.length;

  while (i < n) {
    const row = [];
    while (i < n) {
      if (text[i] === '"') {
        // Quoted field
        i++; // skip opening quote
        let val = '';
        while (i < n) {
          if (text[i] === '"') {
            if (text[i + 1] === '"') {
              val += '"';
              i += 2;
            } else {
              i++; // skip closing quote
              break;
            }
          } else {
            val += text[i++];
          }
        }
        row.push(val);
      } else {
        // Unquoted field
        let val = '';
        while (i < n && text[i] !== ',' && text[i] !== '\n' && text[i] !== '\r') {
          val += text[i++];
        }
        row.push(val);
      }
      if (i < n && text[i] === ',') { i++; continue; }
      break;
    }
    // Skip CRLF or LF
    if (i < n && text[i] === '\r') i++;
    if (i < n && text[i] === '\n') i++;
    if (row.length > 0 && !(row.length === 1 && row[0] === '')) rows.push(row);
  }
  return rows;
}

// --- Clean markdown content ---
function cleanContent(raw) {
  if (!raw) return '';

  // Remove YAML front matter (--- ... ---)
  raw = raw.replace(/^---[\s\S]*?---\s*/m, '');

  // Remove SVG class definitions (CSS strings in JS-rendered pages)
  raw = raw.replace(/\.cls-\d+\{[^}]*\}/g, '');

  // Remove lines that are purely SVG/CSS artifact lines
  raw = raw.replace(/^[.#][\w-]+\{.*\}$/gm, '');

  // Remove "Send feedback" nav lines
  raw = raw.replace(/^Send feedback\s*$/gm, '');
  raw = raw.replace(/^Was this helpful\?\s*$/gm, '');
  raw = raw.replace(/^Stay organized with collections\s*$/gm, '');
  raw = raw.replace(/^Save and categorize content based on your preferences\.\s*$/gm, '');

  // Remove breadcrumb nav blocks (lines that are only markdown links)
  raw = raw.replace(/^-\s+\[.*\]\(https?:\/\/[^\)]+\)\s*$/gm, '');

  // Remove "On this page" table of contents blocks
  raw = raw.replace(/^-\s+On this page\s*$/gm, '');
  raw = raw.replace(/^-\s+\[.*\]\(#.*\)\s*$/gm, '');

  // Collapse 3+ blank lines to 2
  raw = raw.replace(/\n{3,}/g, '\n\n');

  return raw.trim();
}

// --- Extract source label from URL ---
function getSource(url) {
  try {
    const u = new URL(url);
    const parts = u.pathname.split('/').filter(Boolean);
    if (parts.length >= 2) return parts.slice(0, 2).join('/');
    return u.hostname;
  } catch {
    return 'google-docs';
  }
}

// --- Semantic chunking ---
const TARGET_WORDS = 300;
const MAX_WORDS = 450;
const MIN_WORDS = 40;

function countWords(text) {
  return text.split(/\s+/).filter(Boolean).length;
}

function splitBySentences(text, maxWords) {
  const sentences = text.match(/[^.!?]+[.!?]+\s*/g) || [text];
  const parts = [];
  let cur = '', curWords = 0;
  for (const s of sentences) {
    const sw = countWords(s);
    if (curWords + sw > maxWords && cur.trim()) {
      parts.push(cur.trim());
      cur = s; curWords = sw;
    } else {
      cur += s; curWords += sw;
    }
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts;
}

function chunkDocument(url, content) {
  const source = getSource(url);
  const paragraphs = content.split(/\n\n+/);
  const chunks = [];
  let buf = [], bufWords = 0;

  function flush() {
    const t = buf.join('\n\n').trim();
    if (countWords(t) < MIN_WORDS) { buf = []; bufWords = 0; return; }

    if (countWords(t) > MAX_WORDS) {
      const parts = splitBySentences(t, MAX_WORDS);
      for (const p of parts) {
        if (countWords(p) >= MIN_WORDS) chunks.push({ url, source, text: p });
      }
    } else {
      chunks.push({ url, source, text: t });
    }
    buf = []; bufWords = 0;
  }

  for (const para of paragraphs) {
    const pw = countWords(para);
    buf.push(para);
    bufWords += pw;
    if (bufWords >= TARGET_WORDS) flush();
  }
  flush();
  return chunks;
}

// --- Main ---
let allChunks = [];
let globalId = 1;

for (const filePath of inputFiles) {
  console.log(`\nParsing: ${filePath}`);
  const text = fs.readFileSync(filePath, 'utf8');
  const rows = parseCSV(text);
  const header = rows[0];
  const snippetIdx = header.findIndex(h => h.toLowerCase().includes('snippet'));
  const urlIdx = 0;

  console.log(`  Rows: ${rows.length - 1}, snippet col: ${header[snippetIdx]}`);

  let pageCount = 0, skippedCount = 0;
  for (let r = 1; r < rows.length; r++) {
    const url = rows[r][urlIdx];
    if (!url || !url.startsWith('http')) continue;
    const raw = snippetIdx !== -1 ? rows[r][snippetIdx] : '';
    const content = cleanContent(raw);
    if (countWords(content) < MIN_WORDS) { skippedCount++; continue; }

    const pageChunks = chunkDocument(url, content);
    for (const c of pageChunks) {
      allChunks.push({ id: globalId++, ...c, word_count: countWords(c.text) });
    }
    pageCount++;
  }
  console.log(`  Pages processed: ${pageCount}, skipped (too short): ${skippedCount}`);
}

// --- Stats ---
console.log(`\nTotal chunks: ${allChunks.length}`);
const wcs = allChunks.map(c => c.word_count);
console.log(`Word count — min: ${Math.min(...wcs)}, avg: ${Math.round(wcs.reduce((a,b)=>a+b,0)/wcs.length)}, max: ${Math.max(...wcs)}`);

// --- Write JSON summary ---
const summaryPath = path.join(outputDir, 'chunks.json');
fs.writeFileSync(summaryPath, JSON.stringify(allChunks, null, 2), 'utf8');
console.log(`Summary: ${summaryPath}`);

// --- Write batches for ingestion (25 chunks each) ---
const BATCH_SIZE = 25;
let batchNum = 1;
for (let i = 0; i < allChunks.length; i += BATCH_SIZE) {
  const batch = allChunks.slice(i, i + BATCH_SIZE);
  const batchPath = path.join(outputDir, `batch_${String(batchNum).padStart(2, '0')}.json`);
  fs.writeFileSync(batchPath, JSON.stringify(batch, null, 2), 'utf8');
  batchNum++;
}
console.log(`Batches written: ${batchNum - 1} (${BATCH_SIZE} chunks each)`);

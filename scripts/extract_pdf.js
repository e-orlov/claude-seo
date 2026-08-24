const fs = require('fs');
const path = require('path');
const pdfParse = require('pdf-parse');

const inputPath = process.argv[2];
if (!inputPath) {
  console.error('Usage: node extract_pdf.js <path-to-pdf>');
  process.exit(1);
}

const outputPath = process.argv[3] || inputPath.replace(/\.pdf$/i, '.txt');

async function extract() {
  const buffer = fs.readFileSync(inputPath);
  const data = await pdfParse(buffer);

  fs.writeFileSync(outputPath, data.text, 'utf8');

  console.log(`Pages:    ${data.numpages}`);
  console.log(`Chars:    ${data.text.length}`);
  console.log(`Output:   ${outputPath}`);
}

extract().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});

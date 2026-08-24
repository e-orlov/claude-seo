const {
  Document, Packer, Paragraph, Table, TableRow, TableCell,
  TextRun, HeadingLevel, AlignmentType, WidthType, BorderStyle,
  ShadingType, convertInchesToTwip, TableLayoutType,
  Header, Footer, PageNumber, NumberFormat
} = require('docx');
const fs = require('fs');
const path = require('path');

// ── Farben ──────────────────────────────────────────────────────────────────
const C = {
  headerBg:   'FFFFFF',  // Tabellen-Header: weißer Hintergrund
  headerText: '000000',
  rowAlt:     'F5F5F5',
  kritisch:   'C00000',
  hoch:       'E26B0A',
  mittel:     'BF8F00',
  niedrig:    '375623',
  white:      'FFFFFF',
  black:      '000000',
  accent:     '1F3864',   // Überschriften-Blau
  lightBlue:  'D6E4F0',   // Abschnitts-Header-Hintergrund
  borderClr:  'BFBFBF',
};

// ── Hilfsfunktionen ──────────────────────────────────────────────────────────
function border(clr = C.borderClr) {
  return { style: BorderStyle.SINGLE, size: 4, color: clr };
}
function allBorders(clr) {
  const b = border(clr);
  return { top: b, bottom: b, left: b, right: b };
}
function noBorders() {
  const n = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  return { top: n, bottom: n, left: n, right: n };
}

function cell(text, opts = {}) {
  const {
    bold = false, italic = false, color = C.black,
    bg = C.white, shade = false, width, vMerge,
    fontSize = 18, align = AlignmentType.LEFT,
    colSpan, rowSpan
  } = opts;

  const runs = [];
  // text kann String oder Array von {text, bold, color} sein
  if (Array.isArray(text)) {
    text.forEach(t => runs.push(new TextRun({
      text: t.text, bold: t.bold ?? bold, color: t.color ?? color,
      size: fontSize, font: 'Calibri'
    })));
  } else {
    // Inline-Code: `...` fett + Courier
    const parts = String(text ?? '').split(/(`[^`]+`)/g);
    parts.forEach(p => {
      if (p.startsWith('`') && p.endsWith('`')) {
        runs.push(new TextRun({ text: p.slice(1, -1), bold: true, font: 'Courier New', size: fontSize, color }));
      } else if (p) {
        runs.push(new TextRun({ text: p, bold, italic, font: 'Calibri', size: fontSize, color }));
      }
    });
  }

  const cellOpts = {
    children: [new Paragraph({ children: runs, alignment: align })],
    borders: allBorders(),
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
  };
  if (shade || bg !== C.white) {
    cellOpts.shading = { type: ShadingType.CLEAR, fill: bg };
  }
  if (width) cellOpts.width = width;
  if (colSpan) cellOpts.columnSpan = colSpan;
  if (rowSpan) cellOpts.rowSpan = rowSpan;

  return new TableCell(cellOpts);
}

function headerCell(text, opts = {}) {
  return cell(text, { bold: true, bg: C.accent, color: C.white, fontSize: 18, ...opts });
}

function sectionHeaderRow(text, cols) {
  return new TableRow({
    children: [cell(text, {
      bold: true, bg: C.lightBlue, color: C.accent,
      fontSize: 18, colSpan: cols
    })]
  });
}

function prioCell(prio) {
  const map = {
    'Kritisch': { bg: C.kritisch, color: C.white },
    'Hoch':     { bg: C.hoch,     color: C.white },
    'Mittel':   { bg: C.mittel,   color: C.white },
    'Niedrig':  { bg: C.niedrig,  color: C.white },
  };
  const s = map[prio] ?? { bg: C.white, color: C.black };
  return cell(prio, { bold: true, bg: s.bg, color: s.color, fontSize: 18, align: AlignmentType.CENTER });
}

function heading(text, level = 1) {
  const sizes = { 1: 36, 2: 28, 3: 24 };
  return new Paragraph({
    children: [new TextRun({
      text, bold: true, color: C.accent,
      size: sizes[level] ?? 24, font: 'Calibri'
    })],
    spacing: { before: level === 1 ? 400 : 240, after: 120 },
  });
}

function para(text, opts = {}) {
  const { bold = false, italic = false, color = C.black, size = 20, spacing } = opts;
  const parts = String(text).split(/(`[^`]+`)/g);
  const runs = parts.map(p => {
    if (p.startsWith('`') && p.endsWith('`')) {
      return new TextRun({ text: p.slice(1, -1), bold: true, font: 'Courier New', size, color });
    }
    return new TextRun({ text: p, bold, italic, font: 'Calibri', size, color });
  });
  return new Paragraph({
    children: runs,
    spacing: spacing ?? { before: 0, after: 120 },
  });
}

function spacer() {
  return new Paragraph({ children: [], spacing: { before: 0, after: 160 } });
}

function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => headerCell(h, {
          width: { size: colWidths[i], type: WidthType.DXA }
        }))
      }),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((cellContent, ci) => {
          const w = { size: colWidths[ci], type: WidthType.DXA };
          const bg = ri % 2 === 0 ? C.white : C.rowAlt;
          if (cellContent && cellContent.__isPrio) return prioCell(cellContent.value);
          if (cellContent && cellContent.__isCell) return cellContent.cell;
          return cell(cellContent, { bg, width: w });
        })
      }))
    ]
  });
}

// ── Dokument aufbauen ────────────────────────────────────────────────────────
const children = [];

// Titelseite
children.push(
  new Paragraph({ children: [], spacing: { before: 1200, after: 0 } }),
  new Paragraph({
    children: [new TextRun({ text: 'Onpage-Report', bold: true, size: 56, color: C.accent, font: 'Calibri' })],
    alignment: AlignmentType.CENTER,
  }),
  new Paragraph({
    children: [new TextRun({ text: 'Indexierbarkeit & Duplicate Content', size: 36, color: '404040', font: 'Calibri' })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 160 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'sos-kartenshop.de  |  Juni 2026', size: 28, color: '606060', font: 'Calibri' })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 1600 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'Erstellt mit Screaming Frog MCP  |  Datenstand: Juni 2026', size: 20, color: '808080', font: 'Calibri' })],
    alignment: AlignmentType.CENTER,
  }),
  // Seitenumbruch nach Titelseite
  new Paragraph({ children: [], pageBreakBefore: true }),
);

// ── 1. Datenbasis ────────────────────────────────────────────────────────────
children.push(heading('1. Datenbasis'));

children.push(makeTable(
  ['Quelle', 'Datei / Tool', 'Stand', 'Scope', 'Limitierung'],
  [[
    'Screaming Frog MCP',
    'Intern HTML, Page Titles, Meta Descriptions, H1, Inhalt (Nahduplikate)',
    'Juni 2026',
    'Alle indexierbaren HTML-URLs sos-kartenshop.de',
    '/grafik/-Dateien mit falschem Content-Type text/html (8 Bild-Assets) wurden in allen Berechnungen ausgeschlossen'
  ]],
  [1400, 2400, 800, 2200, 2800]
));

children.push(spacer());

// ── 2. Basis-Zahlen ──────────────────────────────────────────────────────────
children.push(heading('2. Basis-Zahlen'));
children.push(para('Hinweis: /grafik/-URLs mit Content-Type text/html sind in allen Zählungen ausgeschlossen.', { italic: true, color: '606060', size: 18 }));

children.push(makeTable(
  ['Kennzahl', 'Wert', 'Anteil', 'Evidenz'],
  [
    ['Alle indexierbaren HTML-URLs mit Status 200', '1.285', '100 % (Gesamtbasis)', 'SF Intern HTML Export'],
    ['davon: mit Parameter (?)', '833', '64,8 % von 1.285', 'SF Intern HTML Export'],
    ['davon: ohne Parameter → Bezugsgröße für Issues #3–#8 (= 100 %)', '452', '35,2 % von 1.285', 'SF Intern HTML Export'],
  ],
  [3800, 900, 1400, 1900]
));

children.push(spacer());

// ── 3. Priorisierte Issue-Tabelle ────────────────────────────────────────────
children.push(heading('3. Priorisierte Issue-Tabelle'));
children.push(para('100 %-Basis durchgehend: 452 indexierbare HTML-URLs ohne Parameter, Status 200 (nach Ausschluss der /grafik/-Pseudo-HTML-URLs).',
  { italic: true, color: '606060', size: 18 }));
children.push(spacer());

// Spaltenbreiten: #, Cluster, Issue, Betr.URLs, Anteil, Prio, SEO-Auswirkung, Empfehlung, Evidenz
const IW = [300, 1200, 2400, 900, 1400, 700, 1600, 2200, 1100];

const issueHeaders = ['#', 'Cluster', 'Issue', 'Betroffene URLs', 'Anteil der betroffenen URLs', 'Prio', 'SEO-Auswirkung', 'Handlungsempfehlung', 'Evidenz'];

const issueRows = [
  [
    '1', '`index.php?page=`',
    'Parameterseiten indexierbar — Warenkorb-Aktionen (?add=, ?remove=, page=18), Legacy-Kategorieseiten (page=9) und weitere index.php-Varianten ohne eigenständigen Content sind indexierbar. Kein redaktioneller Inhalt, keine Canonical-Zuweisung, keine H1 oder Title.',
    '439 von 1.285', '34,2 % aller indexierbaren URLs mit Status 200',
    { __isPrio: true, value: 'Kritisch' },
    'Massiver Crawl-Budget-Verlust, Index-Bloat, Duplicate Content gegenüber clean URLs',
    '`Disallow: /index.php` in robots.txt. Legacy-Kategorieseiten (page=9) zusätzlich per 301 auf clean-URL-Äquivalente umleiten, sobald der Disallow greift.',
    'SF Intern HTML Export'
  ],
  [
    '2', '`ajaxLoader.php?`',
    'Ajax-API-Endpoints indexierbar — 392 Lagerprüf- und Produktlisten-Requests ohne vollständiges HTML-Dokument, ohne Title, ohne H1. Screaming Frog klassifiziert sie als indexierbar.',
    '392 von 1.285', '30,5 % aller indexierbaren URLs mit Status 200',
    { __isPrio: true, value: 'Kritisch' },
    'Crawl-Budget-Verlust, Index-Bloat, kein SEO-Wert',
    '`Disallow: /ajaxLoader.php` in robots.txt.',
    'SF Intern HTML Export'
  ],
  [
    '3', 'no-param-URLs: Produktdetailseiten, Systemseiten',
    'Near-Duplicate Content ≥ 98 % — 218 von 452 no-param-URLs mit Ähnlichkeit ≥ 98 % zu mindestens einer weiteren URL. Darunter 121 URLs bei 100 % (faktisch identisch) — u.a. Systemseiten mit generischem Seiteninhalt (je 406 Duplikat-Partner) und Produktdetailseiten ohne variantenspezifischen Content.',
    '218 von 452', '48,2 % aller indexierbaren no-param-URLs',
    { __isPrio: true, value: 'Kritisch' },
    'Canonical-Selektion durch Google, Ranking-Unterdrückung beider URLs im Paar',
    'Systemseiten ohne Rankingwert: `noindex`. Produktseiten: Canonical auf kanonische Variante + variantenspezifische Merkmale in Content einbauen.',
    'SF Inhalt – Nahduplikate Export'
  ],
  [
    '4', 'no-param-URLs: Produkt- und Kategorieseiten',
    'Near-Duplicate Content 90–97 % — 150 von 452 no-param-URLs mit Ähnlichkeit 90–97 %. Ursache: identische Template-Elemente auf Produkt- und Kategorieseiten bei fehlendem differenzierendem Content.',
    '150 von 452', '33,2 % aller indexierbaren no-param-URLs',
    { __isPrio: true, value: 'Hoch' },
    'Ranking-Dilution im Cluster, Sichtbarkeitskonzentration auf wenige URLs',
    'Content-Differenzierungsstrategie: Unique Value Blocks pro Seitentyp (Kategorietexte, produktspezifische Merkmale). Für 96–97 %-Gruppe Canonical-Tags prüfen.',
    'SF Inhalt – Nahduplikate Export'
  ],
  [
    '5', 'no-param-URLs: Produkt- und Kategorieseiten',
    'Duplizierte Meta Description — 385 von 452 no-param-URLs tragen eine von wenigen generischen Beschreibungen: 289 URLs mit identischer sitewide Description, 73 mit einer zweiten Variante. Google ersetzt generische Descriptions durch eigene Snippets.',
    '385 von 452', '85,2 % aller indexierbaren no-param-URLs',
    { __isPrio: true, value: 'Hoch' },
    'CTR-Verlust in SERPs, fehlende Keyword-Differenzierung im Snippet',
    'Meta-Description-Template nach Seitentyp einführen: [Produktname/Kategorie] – [USP/Charakteristik] – SOS-Kartenshop. Mindestens Kategorie- und Produktebene individualisieren.',
    'SF Meta Descriptions Export'
  ],
  [
    '6', 'no-param-URLs: Produktdetailseiten (/weihnachtskarten/, /grusskarten/)',
    'Duplizierter Meta Title — 65 von 452 no-param-URLs mit identischen Titeln. Häufigster Fall: generischer Fallback-Titel auf 33 URLs, weitere Fälle auf Produktgruppen-Seiten (je 3 URLs). Kein Keyword-Targeting für betroffene URLs.',
    '65 von 452', '14,4 % aller indexierbaren no-param-URLs',
    { __isPrio: true, value: 'Hoch' },
    'Kein Keyword-Targeting, Google kann Seiten nicht für individuelle Queries differenzieren',
    'Title-Template nach Seitentyp einführen: [Kategoriename/Produktname] – [Unterkategorie/Merkmal] – SOS-Kartenshop.',
    'SF Page Titles Export'
  ],
  [
    '7', 'no-param-URLs: Kategorieseiten und Produktvarianten (/weihnachtskarten/, /adventskalender/)',
    'Fehlender H1 — 49 von 452 no-param-URLs ohne H1. Schwerpunkte: /weihnachtskarten/-Seiten (17), /adventskalender/-Seiten (6).',
    '49 von 452', '10,8 % aller indexierbaren no-param-URLs',
    { __isPrio: true, value: 'Mittel' },
    'Fehlendes On-Page-Keyword-Signal',
    'H1 dynamisch aus Kategoriename bzw. Produkttitel befüllen. Paginierungsseiten: H1 der Root-Kategorie erben oder `noindex` setzen.',
    'SF H1 Export'
  ],
  [
    '8', 'no-param-URLs: Kategorieseiten (/grusskarten/, /kuverts/, /briefpapiere/)',
    'Duplizierter H1 — 24 von 452 no-param-URLs mit identischen H1-Texten auf mehreren Unterkategorie- oder Paginierungsseiten.',
    '24 von 452', '5,3 % aller indexierbaren no-param-URLs',
    { __isPrio: true, value: 'Niedrig' },
    'Schwaches Differenzierungssignal, Kannibalisierungsrisiko',
    'H1-Texte auf Subkategorie-Ebene differenzieren. Im Zuge der Title-/Description-Template-Überarbeitung mitnehmen.',
    'SF H1 Export'
  ],
  [
    '9', '`*.html?utm_source=cmp`',
    'UTM-Parameter auf Pflichtseiten indexierbar — datenschutz.html und impressum.html mit ?utm_source=cmp sind indexierbar und erzeugen Canonical-Konflikte mit den parameterfreien Originalseiten.',
    '2 von 1.285', '0,2 % aller indexierbaren URLs mit Status 200',
    { __isPrio: true, value: 'Niedrig' },
    'Canonical-Risiko auf Pflichtseiten',
    '`rel="canonical"` auf die parameterfreie URL. UTM-Parameter in Google Search Console als Parameter ohne Seiteneinfluss konfigurieren.',
    'SF Intern HTML Export'
  ],
];

children.push(makeTable(issueHeaders, issueRows, IW));
children.push(spacer());

// ── 4. Near-Duplicate-Bänder ──────────────────────────────────────────────────
children.push(heading('4. Near-Duplicate-Bänder'));
children.push(para('Basis: 452 indexierbare no-param-URLs = 100 %', { italic: true, color: '606060', size: 18 }));
children.push(spacer());

const NDW = [1500, 1000, 1600, 900, 2800, 1800];
const ndHeaders = ['Similarity-Band', 'Betroffene URLs', 'Anteil von 452', 'Schwere', 'Google-Risiko', 'Evidenz'];
const ndRows = [
  ['100 % (faktisch identisch)', '121', '26,8 %', { __isPrio: true, value: 'Kritisch' }, 'Vollständige Ranking-Unterdrückung; Google wählt einen Canonical-Vertreter', 'SF Inhalt – Nahduplikate Export'],
  ['98–99 %', '97', '21,5 %', { __isPrio: true, value: 'Kritisch' }, 'Canonical-Selektion durch Google fast sicher', 'SF Inhalt – Nahduplikate Export'],
  ['96–97 %', '47', '10,4 %', { __isPrio: true, value: 'Hoch' }, 'Inhalt quasi identisch; Ranking-Dilution im Cluster', 'SF Inhalt – Nahduplikate Export'],
  ['93–95 %', '57', '12,6 %', { __isPrio: true, value: 'Hoch' }, 'Kanonische Auswahl wahrscheinlich', 'SF Inhalt – Nahduplikate Export'],
  ['90–92 %', '46', '10,2 %', { __isPrio: true, value: 'Mittel' }, 'Google erkennt Verwandtschaft; Ranking-Dilution möglich', 'SF Inhalt – Nahduplikate Export'],
  [
    { __isCell: true, cell: cell('Gesamt ≥ 90 %', { bold: true, bg: C.rowAlt }) },
    { __isCell: true, cell: cell('368', { bold: true, bg: C.rowAlt }) },
    { __isCell: true, cell: cell('81,4 %', { bold: true, bg: C.rowAlt }) },
    { __isPrio: true, value: 'Kritisch' },
    { __isCell: true, cell: cell('', { bg: C.rowAlt }) },
    { __isCell: true, cell: cell('SF Inhalt – Nahduplikate Export', { bg: C.rowAlt }) },
  ],
];

children.push(makeTable(ndHeaders, ndRows, NDW));
children.push(spacer());

// ── 5. Cluster-Extreme ────────────────────────────────────────────────────────
children.push(heading('5. Cluster-Extreme: URLs mit den meisten Duplikat-Partnern'));
children.push(spacer());

const CEW = [2600, 900, 800, 1100, 2400, 1800];
const ceHeaders = ['URL-Cluster', 'Near-Dup.-Partner', 'Similarity', 'Seitentyp', 'Handlungsempfehlung', 'Evidenz'];
const ceRows = [
  [
    'support-formular.html, email-vergessen-*.html, merkliste.html',
    'je 406', '100 %', 'Systemseiten mit generischem Seiteninhalt',
    '`noindex` prüfen; kein eigenständiger Rankingwert erwartet',
    'SF Inhalt – Nahduplikate Export'
  ],
  [
    'Produktdetailseiten /weihnachtskarten/*/[ID]-*.html u.ä.',
    'je 119', '98–100 %', 'Produktdetailseiten ohne variantenspezifischen Content',
    'Canonical auf kanonische Produktvariante; variantenspezifische Merkmale in Content einbauen',
    'SF Inhalt – Nahduplikate Export'
  ],
  [
    'Kategorie-/Paginierungsseiten /weihnachtskarten/, /grusskarten/, /adventskalender/',
    'je 2–15', '96–100 %', 'Kategorie-Root und Paginierungsseiten mit identischem Template',
    'Canonical der Paginierungsseiten auf Root-Kategorie-URL; Unique Category Content ergänzen',
    'SF Inhalt – Nahduplikate Export'
  ],
];

children.push(makeTable(ceHeaders, ceRows, CEW));
children.push(spacer());

// ── Dokument erzeugen ─────────────────────────────────────────────────────────
const doc = new Document({
  numbering: { config: [] },
  styles: {
    default: {
      document: {
        run: { font: 'Calibri', size: 20, color: C.black },
        paragraph: { spacing: { after: 120 } },
      },
    },
  },
  sections: [{
    properties: {
      page: {
        margin: {
          top: convertInchesToTwip(1),
          bottom: convertInchesToTwip(1),
          left: convertInchesToTwip(0.9),
          right: convertInchesToTwip(0.9),
        },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: 'Onpage-Report – sos-kartenshop.de  |  Juni 2026', size: 16, color: '808080', font: 'Calibri' }),
          ],
          alignment: AlignmentType.RIGHT,
          border: { bottom: border('BFBFBF') },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: 'Seite ', size: 16, color: '808080', font: 'Calibri' }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '808080', font: 'Calibri' }),
            new TextRun({ text: ' von ', size: 16, color: '808080', font: 'Calibri' }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: '808080', font: 'Calibri' }),
          ],
          alignment: AlignmentType.CENTER,
        })],
      }),
    },
    children,
  }],
});

const outPath = path.join('C:\\Users\\Evgeniy\\Downloads', 'Onpage-Report_sos-kartenshop_2026-06.docx');
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log('OK: ' + outPath);
}).catch(err => {
  console.error('FEHLER:', err.message);
  process.exit(1);
});

# Onboarding-Prompt: SEO-Setup auf einem neuen Windows-Rechner einrichten

> Dieses Dokument ist ein vollständiger Prompt. Kopiere den gesamten Inhalt ab der
> nächsten Zeile in eine frische Claude Code Session auf dem neuen Rechner.

---

Du richtest auf diesem (neuen, frischen) Windows-Rechner dieselbe Arbeitsumgebung
ein, die auf einem anderen Rechner bereits für datei-basierte SEO-Audits mit Claude
Code produktiv läuft. Es gibt vier Bereiche: Software-Voraussetzungen, drei/vier
MCP-Server, Skills, und CLAUDE.md-Policies. Arbeite die Phasen der Reihe nach ab.
Prüfe nach jedem Schritt, ob er funktioniert hat, und behebe Fehler eigenständig,
bevor du weitermachst — frage den Nutzer nur, wenn eine echte Entscheidung nötig ist
(z. B. Lizenzdaten, Zugangsdaten, ob ein optionaler Schritt gewünscht ist), nicht bei
technischen Fehlern, die du selbst diagnostizieren und lösen kannst.

Alle Pfade unten sind relativ zu `%USERPROFILE%` (also `C:\Users\<dein-windows-user>`)
zu verstehen, auch wenn konkrete Beispiele mit einem Platzhalter-Namen geschrieben
sind. Ersetze ihn durch den tatsächlichen Benutzernamen dieses Rechners.

## Kontext: was hier eingerichtet wird

Ein Git-Repo mit dem kompletten Werkzeugkasten wurde bereits vorbereitet:
`https://github.com/e-orlov/claude-seo` (öffentliches Repo — Klonen ohne Login möglich). Es enthält:

- `CLAUDE.md` — Projekt-Policy für datei-basierte SEO-Audits (strikt: keine Live-Crawls,
  keine APIs, keine OAuth, alles nur aus hochgeladenen Dateien)
- `global/CLAUDE.md` — projektübergreifende Policy (Qdrant-Memory-Mechanik,
  DuckDB-Staging-Regel, Humanizer-Pflicht für alle Texte)
- `global/skills/humanizer/SKILL.md` — Skill, der KI-typische Schreibmuster aus Texten entfernt
- `.claude/skills/*` — elf SEO-Audit-Skills (Datenfundament, Clustering, technische/
  Content-/Backlink-/GEO-/Performance-Diagnose, Scoring, Report-Generator, Redirect-Map-Builder)
- `generate_report.js`, `scripts/*.js` — Report- und Wissensbasis-Ingestion-Tooling
- `global/scripts/qdrant_mcp_start.py`, `global/scripts/qdrant-server-config.yaml` —
  Start-Skript und Config für den lokalen Qdrant-Vektor-Server

**Bewusst nicht im Repo** (und das ist beabsichtigt, nicht vergessen):
- `clients/` — echte Kundendaten aus Audits. Bleiben pro Maschine lokal, nicht geteilt.
- `knowledge/` — Buchauszüge ("The Art of SEO", 4th Ed.) und gescrapte Google-Docs-Inhalte,
  die die SEO-Wissensbasis in Qdrant füttern. Urheberrechtlich nicht für Weitergabe per Git
  geeignet — wird stattdessen lokal auf diesem Rechner neu erzeugt (siehe Phase 5).

---

## Phase 1 — Software-Voraussetzungen

Prüfe für jede Zeile zuerst, ob sie schon erfüllt ist, bevor du installierst.

### 1.1 Git for Windows
```bash
git --version
```
Ziel: 2.5x, mit Git Credential Manager (ist im Windows-Installer seit einigen Jahren
gebündelt — prüfe mit `git credential-manager --version`). Falls nicht vorhanden:
```bash
winget install --id Git.Git -e --source winget
```
Nach Installation neue Shell öffnen, damit PATH aktualisiert ist, dann erneut testen.

### 1.2 Node.js + npm
```bash
node --version
npm --version
```
Ziel: Node 20 LTS oder neuer (Referenzmaschine läuft auf v24.16.0). Falls fehlend:
```bash
winget install --id OpenJS.NodeJS.LTS -e
```

### 1.3 Python
```bash
python --version
```
Ziel: 3.12.x. Falls fehlend:
```bash
winget install --id Python.Python.3.12 -e
```
Danach den Report-Generator-Skill mit seiner Python-Abhängigkeit ausstatten:
```bash
python -m pip install python-docx
```
Test:
```bash
python -c "import docx; print('python-docx OK', docx.__version__)"
```

### 1.4 uv (Astral) — Achtung: AppData\Roaming-Falle
Installiere:
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**Wichtiges bekanntes Problem auf diesem Setup:** Wenn `uv` seinen Cache/Tools-Ordner
standardmäßig unter `%APPDATA%` (`AppData\Roaming`) ablegt, kann das in manchen
Claude-Code-/Sandbox-Konfigurationen ein Junction/Redirect sein, das nicht auf das
echte Dateisystem zeigt — Tools landen dann in einem unsichtbaren Schattenordner und
funktionieren nicht zuverlässig. Lege deshalb explizit Cache- und Tool-Verzeichnisse
außerhalb von `AppData\Roaming` an und setze sie als persistente Environment
Variablen (System- oder Benutzerebene, nicht nur für die aktuelle Shell):
```bash
mkdir -p "$USERPROFILE/uv-cache" "$USERPROFILE/uv-tools"
setx UV_CACHE_DIR "%USERPROFILE%\uv-cache"
setx UV_TOOL_DIR "%USERPROFILE%\uv-tools"
```
Neue Shell öffnen, dann testen:
```bash
uv --version
uv tool run --with "mcp<2.0.0" duckdb-mcp-server --help
```
Wenn der zweite Befehl fehlschlägt oder hängt, ist das fast immer die
Roaming-Falle — prüfe mit
`powershell -c "Get-Item $env:APPDATA | Select-Object LinkType,Target"`,
ob `AppData\Roaming` ein Junction ist, und stelle sicher, dass `UV_CACHE_DIR`/
`UV_TOOL_DIR` wirklich außerhalb davon zeigen.

### 1.5 Google Chrome
Für den `chrome-devtools`-MCP-Server wird ein installiertes Chrome (oder Chromium-
basiert) benötigt. Prüfen, ob vorhanden; falls nicht:
```bash
winget install --id Google.Chrome -e
```

### 1.6 Screaming Frog SEO Spider — Prüfungs- und Diagnoseweiche

Screaming Frog ist in den meisten Fällen auf diesem Rechner schon installiert,
oft schon lange vor diesem Setup, eigenständig vom Nutzer. **Prüfe deshalb immer
zuerst den Ist-Zustand, bevor du installierst oder Konfiguration änderst** — geh
Schritt für Schritt vor, jeder Schritt entscheidet, was als Nächstes nötig ist.

Port `11435` ist Screaming Frogs eigener, fester Standard-Port für den seit
Version 24.0 nativ eingebauten MCP-Server (`Settings → MCP Server` in der App;
das Feature existiert in älteren Versionen schlicht nicht). Die App spricht nur
"streamable HTTP", Claude erwartet stdio — deshalb übersetzt `mcp-remote`
dazwischen (Phase 3, `seospider`-Eintrag). **Wichtig:** Screaming Frog ist kein
Hintergrunddienst — die Anwendung muss während der gesamten Session offen
bleiben. Wird sie geschlossen, sind die MCP-Tools sofort weg, auch wenn Port und
Root-Verzeichnis korrekt konfiguriert sind.

**Schritt A — Ist Screaming Frog überhaupt installiert?**
```bash
ls "/c/Program Files (x86)/Screaming Frog SEO Spider" 2>/dev/null || ls "/c/Program Files/Screaming Frog SEO Spider" 2>/dev/null
```
- Gefunden → weiter zu Schritt B.
- Nicht gefunden → installieren: Download-Installer von
  https://www.screamingfrog.co.uk/seo-spider/ (winget-Paket existiert nicht
  zuverlässig für dieses Tool, daher direkter Download). Danach weiter zu Schritt B.

**Schritt B — Läuft die Anwendung gerade?**
```bash
tasklist | grep -i "ScreamingFrogSEOSpider"
```
- Läuft → weiter zu Schritt C.
- Läuft nicht → **hier ist echte Nutzerinteraktion nötig, nicht automatisierbar**:
  Screaming Frog ist eine GUI-Anwendung und erwartet beim ersten Start in dieser
  Session ggf. Lizenz-/Update-Dialoge. Bitte den Nutzer, die Anwendung einmal
  manuell zu öffnen und offen zu lassen, dann mit Schritt C weiterfahren.

**Schritt C — Ist der eingebaute MCP-Server konfiguriert?**
```bash
grep "^mcpserver\." "$USERPROFILE/.ScreamingFrogSEOSpider/spider.config" 2>/dev/null
```
Erwartet z. B.:
```
mcpserver.auto_start=false
mcpserver.port=11435
mcpserver.root=C:\Users\<user>\seo_spider_mcp_server
mcpserver.node_scripting=false
mcpserver.max_response_size_bytes=100000
```
- Zeilen vorhanden, `mcpserver.port` gesetzt → weiter zu Schritt D.
- Zeilen fehlen oder Datei existiert nicht (ältere Version ohne MCP-Feature, oder
  noch nie konfiguriert) — zwei Fälle, je nach Ergebnis von Schritt B:
  - **Screaming Frog läuft nicht**: Werte direkt in der (geschlossenen App)
    Config-Datei ergänzen — Ordner vorher anlegen:
    ```bash
    mkdir -p "$USERPROFILE/seo_spider_mcp_server"
    ```
    dann in `spider.config` die fünf Zeilen oben setzen (Root-Pfad an
    `%USERPROFILE%` anpassen), Nutzer bitten, die Anwendung zu öffnen, weiter zu
    Schritt D.
  - **Screaming Frog läuft bereits**: die Config-Datei jetzt NICHT direkt
    anfassen (wird beim Beenden der App ggf. überschrieben) — stattdessen dem
    Nutzer die Fundstelle in der UI nennen (Menü `Configuration` → Suche nach
    "MCP Server"/API-Zugriff; genaue Bezeichnung variiert je Version) und um
    Aktivierung mit Port `11435` bitten. Existiert die Option in der UI gar
    nicht, ist die installierte Version zu alt — Update nötig über
    "Help → Check for Updates" (wieder Nutzerinteraktion), danach erneut prüfen.

**Schritt D — Antwortet der Endpoint tatsächlich?**
```bash
curl -s http://127.0.0.1:11435/mcp
```
- JSON-Fehler über fehlende Header (`"text/event-stream required..."`) →
  **Erfolgssignal**, der Server antwortet und ist erreichbar.
- Verbindung abgelehnt/Timeout → in dieser Reihenfolge erneut prüfen:
  1. Läuft die Anwendung noch (Schritt B)?
  2. Steht `mcpserver.port` wirklich auf `11435` (Schritt C) — falls der Nutzer
     einen anderen Port gewählt hat, muss auch der `seospider`-Block in Phase 3
     diesen Port statt `11435` verwenden, nicht 11435 erzwingen.
  3. Ist der Server in der UI wirklich aktiviert (nicht nur `auto_start=false`
     gesetzt, sondern auch einmal gestartet)?
  4. Firewall/Antivirus, das lokale Ports blockiert (selten) — im Log
     `%USERPROFILE%\.ScreamingFrogSEOSpider\trace.txt` nach Fehlern suchen.

**Lizenzhinweis (separat von der MCP-Konfiguration):** Ohne gültige Lizenz läuft
Screaming Frog im Trial-Modus mit 500-URL-Crawl-Limit. Der MCP-Server lässt sich
davon unabhängig konfigurieren und testen, aber tatsächliche Audit-Crawls über
dieses Limit hinaus brauchen eine aktive Lizenz (`Licence` → `Enter Licence Key`
in der UI). Lizenzdaten dafür vom Nutzer erfragen, falls noch nicht hinterlegt —
das ist eine echte Entscheidung/Zugangsdaten-Frage, kein technischer Fehler.

### 1.7 Qdrant-Server (lokale Vektor-Datenbank für Memory + SEO-Wissensbasis)
Lade das aktuelle Windows-Release von https://github.com/qdrant/qdrant/releases
(Asset mit "windows" im Namen), entpacke `qdrant.exe` nach `%USERPROFILE%\uv-bin\qdrant.exe`.

Lege die Server-Config an (Vorlage liegt im Repo unter `global/scripts/qdrant-server-config.yaml`):
```bash
mkdir -p /c/qdrant-server
cp global/scripts/qdrant-server-config.yaml /c/qdrant-server/config.yaml
```
Storage-Pfad in der Config ist relativ (`./storage`) und liegt damit unter
`C:\qdrant-server\storage`.

Test manuell:
```bash
"$USERPROFILE/uv-bin/qdrant.exe" --config-path C:\qdrant-server\config.yaml
```
(in einem eigenen Terminal laufen lassen, dann in einem zweiten testen:)
```bash
curl -s http://127.0.0.1:6333/collections
```
Ein dauerhaft laufender Scheduled Task ist **nicht nötig** — auf der Referenzmaschine
gibt es aktuell keinen, trotzdem läuft der Server zuverlässig, weil
`qdrant_mcp_start.py` (aus Phase 3) bei jeder Verbindung selbst prüft, ob Port 6333
schon offen ist, und `qdrant.exe` sonst automatisch startet. Nur falls du lieber
einen dauerhaft laufenden Prozess ab Systemstart willst, richte optional einen
Scheduled Task ein (`schtasks /create` oder Task Scheduler).

**Bekannte Eigenheiten, kein Bug:**
- Mehrere gleichzeitig offene Claude-Code-Sessions erzeugen jeweils einen eigenen
  `mcp-server-qdrant.exe`-Prozess, die alle gegen denselben `qdrant.exe`-Server auf
  Port 6333 sprechen. Das ist normal und kein Zombie-Prozess-Problem, solange der
  Server selbst antwortet (`curl http://127.0.0.1:6333/collections`).
- Die eigentliche Unzuverlässigkeit lag nicht am Server, sondern an einer nicht
  umsetzbaren Regel im alten `global/CLAUDE.md`: "bei ~70% Kontext-Füllstand
  proaktiv `/compact` aufrufen" — dafür gibt es kein Werkzeug und keine Anzeige des
  Füllstands, die Regel konnte nie greifen. Das aktuelle `global/CLAUDE.md` in
  diesem Repo hat das bereits korrigiert: Memories werden jetzt sofort beim
  Entstehen gespeichert statt auf einen (nie eintretenden) Kompaktierungs-Hinweis
  zu warten.

---

## Phase 2 — Git-Repo klonen

Das Repo ist öffentlich — kein GitHub-Login, kein Git Credential Manager, keine
Zugangsdaten nötig, solange nur geklont/gepullt wird (anonymer HTTPS-Zugriff reicht):
```bash
mkdir -p "$USERPROFILE/Claude-Projects"
cd "$USERPROFILE/Claude-Projects"
git clone https://github.com/e-orlov/claude-seo.git seo
```
Nur falls von diesem Rechner später auch **zurückgeschrieben** werden soll (Push),
braucht es einen GitHub-Account mit Schreibrechten auf das Repo und einen
Browser-Login über Git Credential Manager beim ersten Push. Für die reine
Einrichtung hier ist das nicht relevant.

Verifiziere:
```bash
ls "$USERPROFILE/Claude-Projects/seo/.claude/skills"
```
Erwartet: 11 Skill-Ordner (u. a. `seo-data-foundation`, `seo-file-audit-orchestrator`,
`seo-report-generator`, `seo-url-clustering`, `redirect-map-builder`, ...).

Node-Abhängigkeiten installieren (für `generate_report.js` / Ingestion-Skripte):
```bash
cd "$USERPROFILE/Claude-Projects/seo"
npm install
```

---

## Phase 3 — MCP-Server konfigurieren

Finde zuerst die Claude-Konfigurationsdatei mit dem `mcpServers`-Block auf diesem
Rechner — je nach installierter Claude-App-Variante liegt sie unter einem von:
```
%APPDATA%\Claude\claude_desktop_config.json
%LOCALAPPDATA%\Claude-3p\claude_desktop_config.json
```
Öffne die vorhandene Datei und ergänze/merge im `mcpServers`-Objekt folgende vier
Einträge (Pfade an den tatsächlichen `%USERPROFILE%` dieses Rechners anpassen —
nicht wortwörtlich mit fremdem Nutzernamen übernehmen):

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "chrome-devtools-mcp@latest"],
      "env": {
        "PATH": "C:\\Program Files\\nodejs;C:\\Windows\\system32;C:\\Windows"
      }
    },
    "seospider": {
      "command": "cmd",
      "args": ["/c", "npx", "mcp-remote", "http://localhost:11435/mcp"],
      "env": {
        "PATH": "C:\\Program Files\\nodejs;C:\\Windows\\system32;C:\\Windows"
      }
    },
    "duckdb": {
      "command": "<USERPROFILE>\\uv-bin\\uv.exe",
      "args": [
        "tool", "run", "--with", "mcp<2.0.0", "duckdb-mcp-server",
        "--db-path", "<USERPROFILE>\\duckdb-data\\main.duckdb"
      ],
      "env": {
        "UV_CACHE_DIR": "<USERPROFILE>\\uv-cache",
        "UV_TOOL_DIR": "<USERPROFILE>\\uv-tools"
      }
    },
    "qdrant-memory": {
      "command": "<PATH-ZU-PYTHON>\\python.exe",
      "args": ["<USERPROFILE>\\uv-bin\\qdrant_mcp_start.py"],
      "env": {
        "UV_CACHE_DIR": "<USERPROFILE>\\uv-cache"
      }
    }
  }
}
```

Ersetze `<USERPROFILE>` durch den vollen Pfad (z. B. `C:\Users\Max`) und
`<PATH-ZU-PYTHON>` durch den Pfad des installierten Python 3.12 (finde ihn mit
`python -c "import sys; print(sys.executable)"`).

Kopiere zuerst das Start-Skript für `qdrant-memory` aus dem geklonten Repo an seinen
Zielort:
```bash
mkdir -p "$USERPROFILE/uv-bin"
cp "$USERPROFILE/Claude-Projects/seo/global/scripts/qdrant_mcp_start.py" "$USERPROFILE/uv-bin/qdrant_mcp_start.py"
```
(`qdrant.exe` liegt dort bereits aus Phase 1.7.)

Speichere die Config-Datei, starte die Claude-App neu (oder lade MCP-Server neu,
falls die App das unterstützt, ohne kompletten Neustart), und teste jeden Server:

- **chrome-devtools**: rufe ein Tool wie `list_pages` auf — sollte eine (ggf. leere)
  Liste liefern, kein Verbindungsfehler.
- **seospider**: Screaming Frog muss laufen und der MCP-Server dort aktiv sein
  (Phase 1.6); rufe `sf_list_allowed_base_directory` auf.
- **duckdb**: rufe eine einfache Query auf, z. B. `SELECT 1`.
- **qdrant-memory**: rufe `qdrant-find` mit einer beliebigen Testanfrage auf — beim
  allerersten Aufruf lädt `mcp-server-qdrant` das Embedding-Modell
  (`all-MiniLM-L6-v2`, ca. 90 MB) herunter, das braucht einmalig Internetzugang und
  etwas Zeit.

Wenn ein Server nicht antwortet: prüfe zuerst, ob der zugrunde liegende Prozess/
Port erreichbar ist (z. B. `curl` gegen den jeweiligen lokalen Port), dann ob Pfade
in der Config zum tatsächlichen Dateisystem dieses Rechners passen, dann ob die
zugehörige Software (Screaming Frog, uv, Python) aus Phase 1 tatsächlich funktioniert.

---

## Phase 4 — Skills + CLAUDE.md übernehmen

Die projekt-lokalen SEO-Skills sind bereits Teil des geklonten Repos unter
`seo/.claude/skills/` — kein zusätzlicher Schritt nötig, sobald das Repo im
richtigen Pfad liegt (`%USERPROFILE%\Claude-Projects\seo`), da Claude Code
Skills relativ zum Arbeitsverzeichnis lädt.

Für projektübergreifende (globale) Policy und den Humanizer-Skill, die für **alle**
Projekte gelten sollen, nicht nur für SEO:
```bash
cp "$USERPROFILE/Claude-Projects/seo/global/CLAUDE.md" "$USERPROFILE/.claude/CLAUDE.md"
mkdir -p "$USERPROFILE/.claude/skills/humanizer"
cp "$USERPROFILE/Claude-Projects/seo/global/skills/humanizer/SKILL.md" "$USERPROFILE/.claude/skills/humanizer/SKILL.md"
```
Falls unter `%USERPROFILE%\.claude\CLAUDE.md` bereits eine Datei mit anderem
Inhalt existiert: nicht blind überschreiben, sondern Inhalte zusammenführen und
den Nutzer informieren, was ergänzt wurde.

Test: starte eine neue Claude-Code-Session im Ordner `seo` und prüfe, dass die
Skills in der Skill-Liste auftauchen (u. a. `seo-file-audit-orchestrator`,
`seo-data-foundation`, `humanizer`). Ein einfacher Funktionstest:
```
/humanizer
```
mit einem kurzen Beispieltext ausführen und prüfen, dass eine Überarbeitung
zurückkommt.

---

## Phase 5 — SEO-Wissensbasis in Qdrant nachbilden (optional, aber empfohlen)

Die Skills rufen `qdrant-find` zu Beginn jeder Diagnose auf, um Hintergrundwissen
aus "The Art of SEO" (4th Edition) und den Google Search Central Docs abzurufen.
Dieser Inhalt wurde bewusst nicht mit dem Repo mitgeliefert (Urheberrecht). Um die
gleiche Wissensbasis lokal aufzubauen:

1. Beschaffe eine eigene, legal erworbene Kopie von "The Art of SEO" (4th Edition)
   als PDF und lege sie z. B. unter `seo/knowledge/art-of-seo.pdf` ab.
2. Nutze die im Repo enthaltenen Ingestion-Skripte:
   ```bash
   cd "$USERPROFILE/Claude-Projects/seo"
   node scripts/extract_pdf.js knowledge/art-of-seo.pdf knowledge/art-of-seo.txt
   node scripts/chunk_book.js
   ```
3. Lies die erzeugten Chunks und speichere sie über `qdrant-store` in die Collection
   `claude_code_memory` (Tag-Konvention beibehalten, siehe Format-Beispiele im
   Skript-Output).
4. Für die Google Search Central Docs: rufe die relevanten Seiten unter
   `developers.google.com/search`, `/crawling`, etc. per WebFetch ab und nutze
   `scripts/chunk_googledocs.js` zum Chunking, dann ebenfalls via `qdrant-store`
   ablegen.

Dieser Schritt ist nicht blockierend — ohne ihn funktionieren alle Audit-Skills
weiterhin, `qdrant-find` liefert dann nur weniger oder keine Hintergrundtreffer.

---

## Phase 6 — Abschluss-Smoketest

Führe zum Schluss einmal komplett durch und bestätige jeden Punkt:

- [ ] `git`, `node`, `npm`, `python`, `uv` melden alle eine Version
- [ ] `git clone` von `claude-seo` erfolgreich, Skills sichtbar
- [ ] Screaming Frog installiert, lizenziert, MCP-Server antwortet auf Port 11435
- [ ] Qdrant-Server läuft dauerhaft (Scheduled Task oder manuell gestartet),
      antwortet auf Port 6333
- [ ] Alle vier MCP-Server (`chrome-devtools`, `seospider`, `duckdb`, `qdrant-memory`)
      sind in der Claude-Config eingetragen und antworten auf einen Testaufruf
- [ ] `~/.claude/CLAUDE.md` (global) und `seo/CLAUDE.md` (Projekt) sind vorhanden
- [ ] `/humanizer` funktioniert
- [ ] Ein SEO-Skill (z. B. `seo-data-foundation`) lässt sich mit einer Testdatei
      anstoßen und arbeitet die erwarteten Schritte ab

Berichte am Ende kurz, welche Punkte funktionieren, welche (falls vorhanden) noch
offen sind (z. B. weil Screaming-Frog-Lizenzdaten fehlen oder die Wissensbasis aus
Phase 5 bewusst übersprungen wurde), und was der Nutzer dafür noch beisteuern muss.

## Hinweis zur Evidenz-Registry

`clients/evidence_registry.md` (globaler Zähler für Evidenz-IDs `E-NNN`) ist bewusst
nicht Teil des Repos. Auf diesem Rechner beginnt die Zählung unabhängig bei `E-001`,
wenn der erste Audit hier startet. Falls eine gemeinsame, rechnerübergreifende
Zählung gewünscht ist, müsste `clients/evidence_registry.md` zusätzlich versioniert
und vor jedem Audit auf beiden Rechnern synchronisiert (`git pull`/`push`) werden —
das ist eine bewusste Entscheidung des Nutzers, keine automatische Vorgabe.

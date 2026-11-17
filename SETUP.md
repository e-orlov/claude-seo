# Onboarding-Prompt: SEO-Setup auf einem neuen Windows-Rechner einrichten

> Dieses Dokument ist ein vollständiger Prompt. Kopiere den gesamten Inhalt ab der
> nächsten Zeile in eine frische Claude Code Session auf dem neuen Rechner.

---

Du richtest auf diesem (neuen, frischen) Windows-Rechner dieselbe Arbeitsumgebung
ein, die auf einem anderen Rechner bereits für datei-basierte SEO-Audits mit Claude
Code produktiv läuft. Es gibt vier Bereiche: Software-Voraussetzungen, drei
MCP-Server (chrome-devtools, duckdb, seospider), Skills und CLAUDE.md-Policies. Arbeite die Phasen der Reihe nach ab.
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

- `CLAUDE.md` — Projekt-Policy für SEO-Audits im **gemischten Modus**: eine
  sanktionierte Live-Quelle (Screaming Frog per eigenem MCP-Server für
  Crawl-Daten — inklusive GSC-, GA4- und PageSpeed-Insights/CrUX-Feldern, wenn
  diese APIs direkt in Screaming Frog verbunden sind), alles andere dateibasiert
  (Ahrefs für Backlinks, Semrush-AI-Visibility-`.mhtml`-Exporte für GEO,
  eigenständige GSC/GA4/WebPageTest/Lighthouse/HAR-Exporte, wenn nicht schon über
  Screaming Frog mitgeliefert). Keine sonstigen Live-APIs, kein OAuth, kein
  chrome-devtools als Standard-Datenquelle (nur wenn der Nutzer es explizit für
  eine konkrete Aufgabe anfragt).
- `global/CLAUDE.md` — projektübergreifende Policy (DuckDB-Staging-Regel,
  Humanizer-Pflicht für alle Texte)
- `global/skills/humanizer/SKILL.md` — Skill, der KI-typische Schreibmuster aus Texten entfernt
- `.claude/skills/*` — sechs SEO-Skills: `seo-url-clustering`,
  `seo-helpful-content-audit`, `seo-geo-audit`, `seo-geo-report-generator`,
  `seo-report-generator`, `redirect-map-builder`. Die acht alten Skills des
  gemischten Datei-Workflows (Datenfundament, Orchestrator, Diagnose, Scoring)
  liegen nur noch auf dem Branch `archive/legacy-file-audit-skills`.
- `.mcp.json` — Projekt-MCP-Server `chrome-devtools` und `duckdb`
- `.claude/skills/seo-report-generator/` — der einzige zulässige Report-Renderer
  (`report_renderer.py` + `docx_helpers.py` + `report_config.py`, Python/`python-docx`).
  Jedes `.docx`-Reporting läuft ausschließlich hierüber, kein eigenständiges
  Report-Script daneben (siehe CLAUDE.md "Report Infrastructure").

**Bewusst nicht im Repo** (und das ist beabsichtigt, nicht vergessen):
- `clients/` — echte Kundendaten aus Audits. Bleiben pro Maschine lokal, nicht geteilt.

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
uvx --with "mcp<2" mcp-server-duckdb --help
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
Erwartet: 6 Skill-Ordner (`seo-geo-audit`, `seo-geo-report-generator`,
`seo-helpful-content-audit`, `seo-report-generator`, `seo-url-clustering`,
`redirect-map-builder`).


---

## Phase 3 — MCP-Server konfigurieren (Claude Code)

Es gibt drei aktive MCP-Server. Zwei davon liegen im Repo, einer wird pro Benutzer
registriert.

| Server | Wo konfiguriert | Wie |
|---|---|---|
| `chrome-devtools` | `.mcp.json` im Repo | kommt mit dem Klonen, nichts zu tun |
| `duckdb` | `.mcp.json` im Repo | kommt mit dem Klonen, Ordner für die Datenbank anlegen |
| `seospider` | Benutzer-Ebene (`~/.claude.json`) | einmalig per Befehl registrieren |

Der Pfad zur DuckDB-Datei in `.mcp.json` nutzt `${USERPROFILE}` und passt sich
damit automatisch an den Windows-Benutzer an. Nichts in `.mcp.json` ändern und
nicht mit einem fremden Benutzernamen committen.

### 3.1 DuckDB-Ordner anlegen
```bash
mkdir -p "$USERPROFILE/duckdb-data"
```
Die Datei `main.duckdb` legt der Server beim ersten Start selbst an. Sie ist
absichtlich nicht im Repo, weil sie Kundendaten enthalten kann.

### 3.2 seospider registrieren (Benutzer-Ebene)
Screaming Frog spricht "streamable HTTP", Claude Code kann das direkt. Ein
Zwischenprogramm wie `mcp-remote` ist nicht nötig.
```bash
claude mcp add --transport http --scope user seospider http://localhost:11435/mcp
```
Falls der Befehl `claude` in der Shell nicht gefunden wird: den Eintrag stattdessen
in `%USERPROFILE%\.claude.json` unter `mcpServers` ergänzen:
```json
"seospider": { "type": "http", "url": "http://localhost:11435/mcp" }
```
Hat der Nutzer in Screaming Frog einen anderen Port gewählt, diesen Port eintragen.

### 3.3 Projekt-Server freigeben
Beim ersten Start in `Claude-Projects\seo` fragt Claude Code, ob die Server aus
`.mcp.json` vertraut werden. Der Nutzer muss das bestätigen. Das lässt sich nicht
automatisieren.

### 3.4 Testen
Claude-Code-Session im Ordner `seo` neu starten und jeden Server prüfen:

- **chrome-devtools**: Tool `list_pages` aufrufen. Eine (ggf. leere) Liste ist OK.
- **seospider**: Screaming Frog muss laufen und der MCP-Server dort aktiv sein
  (Phase 1.6). Tool `sf_allowed_base_directory` aufrufen.
- **duckdb**: Query `SELECT 1` ausführen.

Wenn ein Server nicht antwortet: zuerst prüfen, ob der zugrunde liegende Prozess
oder Port erreichbar ist (z. B. `curl http://127.0.0.1:11435/mcp`), dann ob `uv`
und Node.js (Phase 1) funktionieren, dann ob die Server in der Session überhaupt
als verbunden gelistet sind.

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
Skills in der Skill-Liste auftauchen (u. a. `seo-url-clustering`,
`seo-report-generator`, `humanizer`). Ein einfacher Funktionstest:
```
/humanizer
```
mit einem kurzen Beispieltext ausführen und prüfen, dass eine Überarbeitung
zurückkommt.

---

## Phase 5 — Abschluss-Smoketest

Führe an dieser Stelle einmal komplett durch und bestätige jeden Punkt — die
jeden Punkt der Liste:

- [ ] `git`, `node`, `npm`, `python`, `uv` melden alle eine Version
- [ ] `git clone` von `claude-seo` erfolgreich, Skills sichtbar
- [ ] Screaming Frog installiert, lizenziert, MCP-Server antwortet auf Port 11435
- [ ] Alle drei MCP-Server (`chrome-devtools`, `seospider`, `duckdb`) sind
      verbunden und antworten auf einen Testaufruf (Phase 3.4)
- [ ] `~/.claude/CLAUDE.md` (global) und `seo/CLAUDE.md` (Projekt) sind vorhanden
- [ ] `/humanizer` funktioniert
- [ ] `seo-url-clustering` findet nach `SHOW TABLES` in DuckDB seine Basistabelle
      (oder meldet sauber, dass noch keine Crawl-Tabelle gestaged ist)

Berichte kurz, welche Punkte funktionieren, welche (falls vorhanden) noch offen
sind (z. B. weil Screaming-Frog-Lizenzdaten fehlen), und was der Nutzer dafür
noch beisteuern muss.

---

## Hinweis zur Evidenz-Registry

`clients/evidence_registry.md` (globaler Zähler für Evidenz-IDs `E-NNN`) ist bewusst
nicht Teil des Repos. Auf diesem Rechner beginnt die Zählung unabhängig bei `E-001`,
wenn der erste Audit hier startet. Falls eine gemeinsame, rechnerübergreifende
Zählung gewünscht ist, müsste `clients/evidence_registry.md` zusätzlich versioniert
und vor jedem Audit auf beiden Rechnern synchronisiert (`git pull`/`push`) werden —
das ist eine bewusste Entscheidung des Nutzers, keine automatische Vorgabe.

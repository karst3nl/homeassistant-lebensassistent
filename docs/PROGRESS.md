# Entwicklungsfortschritt

## Stand
- Status: **Etappen 0.1 und 0.2 lokal implementiert und geprüft**; Freigabepause.
- Aktiver Branch: `alpha`; `main` nur Platzhalter, nicht bearbeiten.
- Zuletzt abgeschlossene Etappe: **0.2** — responsive Basisoberfläche, Navigation, Theme und lokale Ingress-Pfadkompatibilität.
- Geprüft: 25 Unit-/API-Tests, 18 echte Chromium-Browsertests, Lint/Format, Lockfile und Paketinhalt. Lokale Präfixsimulation ersetzt keinen HA-Laufzeittest.
- Noch nicht geprüft: Home-Assistant-Integration, Ingress, ARM-/Raspberry-Pi-Betrieb. Datenbankmigrationen sind mangels Datenbank noch nicht anwendbar.
- Nächster Schritt: **Explizite Nutzerfreigabe für Etappe 0.3 abwarten**; noch keine Arbeiten daran begonnen.

## Etappenlog
| Etappe | Status | Tests | Freigabe |
|---|---|---|---|
| 0.1 Grundgerüst und Health | Lokal abgeschlossen | 3 API-Tests grün; weiterhin Teil der Regression | Fortsetzung mit „weiter“ freigegeben |
| 0.2 Responsive UI | Lokal abgeschlossen | 25 API-Tests und 18 Browsertests grün; Lint/Format und Paketinhalt geprüft | Ergebnis zur Abnahme vorgelegt |
| 0.3 HA-App/Ingress | Offen | — | Ausstehend |
| 0.4 SQLite/Migration | Offen | — | Ausstehend |
| 1.x–7.x | Offen | — | Ausstehend |

Nach jeder Mini-Etappe ausfüllen: Änderung, betroffene Dateien, Testbefehle mit Ergebnis, bekannte Probleme, Datenschutzcheck, Commit-SHA und Freigabe.

## Etappe 0.1 — 2026-11-14

### Änderungen und Verhalten

- `src/lebensassistent/main.py`: isoliert erzeugbare FastAPI-App und ASGI-Einstiegspunkt.
- `src/lebensassistent/api/health.py` und Paketdateien: einziger registrierter Endpunkt `GET /health`, HTTP 200 mit `{"status":"ok"}`; keine externen Zugriffe oder Schreiboperationen.
- `tests/test_health.py`: synthetische API-Anfragen für Health, abgelehntes POST (405) und unbekannten Pfad (404).
- `.python-version`, `pyproject.toml`, `uv.lock`: Python 3.12.14, exakt versionierte direkte Abhängigkeiten und Build-Backend; transitive Versionen und Prüfsummen im Lockfile; pytest- und Ruff-Konfiguration.
- `README.md`, `docs/DEVELOPMENT.md`: Einstieg, Projektstruktur, reproduzierbare Einrichtung sowie Start-/Stopp- und Testanleitung. Statusangaben in Etappenplan und Architektur aktualisiert.
- Keine Datenbank, Finanzlogik, UI oder HA-Verpackung implementiert.

### Tatsächlich ausgeführte Prüfungen

Ausgangscommit auf `alpha`: `46b46ca64adde91cf476be331f3dfdafb3b879b6`.
Geprüft wurde der darauf aufbauende Arbeitsstand dieser Etappe, unter Linux
x86_64 mit Python **3.12.14** und uv **0.13.6**. pytest **9.2.0**, Ruff
**0.17.5**, FastAPI **0.162.7** und Uvicorn **0.54.0** stammen aus `uv.lock`.

| Befehl / Prüfung | Tatsächliches Ergebnis |
|---|---|
| `uv sync --locked` | Neue lokale `.venv` erfolgreich eingerichtet; lokales Paket gebaut und installiert |
| `uv run --locked pytest tests/test_health.py` | **3 passed** (0,32 s) |
| `uv run --locked pytest` | Vollständige vorhandene Suite: **3 passed** (0,25 s) |
| `uv run --locked ruff check .` | **All checks passed!** |
| `uv run --locked ruff format --check .` | Erfolgreich; keine Formatänderungen erforderlich |
| `uv lock --check` | Erfolgreich; Lockfile und Projektdefinition konsistent |
| Frische zweite Umgebung über `UV_PROJECT_ENVIRONMENT`, danach `uv sync --locked` und dieselben pytest-/Ruff-Befehle | Einrichtung erfolgreich; erneut **3 passed** (0,58 s), Lint/Format grün |
| `uv run --locked uvicorn lebensassistent.main:app --host 127.0.0.1 --port 8000` | Prozess gestartet; Application startup complete |
| `curl --fail-with-body --silent --show-error --max-time 10 --include http://127.0.0.1:8000/health` | **HTTP/1.1 200 OK**, `application/json`, `{"status":"ok"}` |
| SIGTERM an den zuvor gestarteten Serverprozess | Geordnet beendet; Application shutdown complete |
| `git diff --cached --check` und unabhängiges Code-Review | Keine Whitespace-Fehler oder offenen Code-Befunde |
| `uvx --from detect-secrets==1.5.0 detect-secrets scan --no-verify` | Keine Funde in den für Git vorgemerkten bzw. bereits versionierten Dateien |

In dieser Cloud-Umgebung wurde `UV_CACHE_DIR` auf ein beschreibbares
Arbeitsverzeichnis gesetzt. Die zweite virtuelle Umgebung und das
Secret-Scan-Protokoll liegen ebenfalls außerhalb des Repositorys.

Tests wurden vor dem Endpunkt angelegt. Der erste Lauf meldete die veraltete
`httpx`-Anbindung des aktuellen Starlette-Testclients; die Entwicklungsabhängigkeit
wurde auf **httpx2 2.16.0** umgestellt. Danach schlug die Testsammlung wie
erwartet am noch fehlenden App-Modul fehl. Nach dessen Implementierung liefen
die oben protokollierten Prüfungen erfolgreich. Es bleiben keine bekannten
Fehler innerhalb von Etappe 0.1.

### Commitnachweis

Implementierung, Tests und Prüfprotokoll sind auf `alpha` im Commit
[`e57179867311e54bb8ac7bf4a62bd492ce850363`](https://github.com/karst3nl/homeassistant-lebensassistent/commit/e57179867311e54bb8ac7bf4a62bd492ce850363)
(`feat: add stage 0.1 FastAPI foundation and health tests`) enthalten.
Der anschließende Dokumentationscommit ergänzt ausschließlich diesen
Hashnachweis. Der Anwendungs- und Testcode entspricht dem geprüften Stand.

### Datenschutz und offene Prüfungen

Vorgemerkten Diff manuell geprüft und automatisierten Secret-Scan ausgeführt.
Die Tests enthalten ausschließlich synthetische HTTP-Anfragen. Es wurden
keine privaten Daten, Zugangsdaten, Datenbanken oder Backups hinzugefügt.
Der Scan lief ohne externe Verifikation möglicher Geheimnisse.

Der Health-Endpunkt ist ein Lebenszeichen des lokalen Webservers und keine
Integrations- oder Datenbankprüfung. **Home Assistant OS, Ingress und
ARM/Raspberry Pi wurden nicht getestet.** Die HA-Verpackung ist erst für
Etappe 0.3 vorgesehen. Zum Abschluss von 0.1 lag noch keine Freigabe für
Etappe 0.2 vor; die anschließende Freigabe ist unten protokolliert.

### Abschlusscheckliste

- [x] Etappe 0.1 implementiert.
- [x] Tests und Start lokal tatsächlich ausgeführt; Lint und Regression grün.
- [ ] HA-Laufzeittest (ausstehend).
- [x] Nutzerfreigabe für Etappe 0.2 durch „weiter“ (2026-11-14).

## Etappe 0.2 — 2026-11-14

### Freigabe und Umfang

Der Nutzer hat nach dem Abschlussbericht zu 0.1 mit **„weiter“** die nächste
Etappe freigegeben. Ausschließlich 0.2 wurde umgesetzt; Ausgangscommit auf
`alpha`: `fbe933af24ecdf06d5127f91399eb025a1071eac`.

### Änderungen

- `src/lebensassistent/api/ui.py`, `main.py`: statische HTML-Ansichten für
  Übersicht und sieben Modulbereiche, lokale Assets und Browser-Fehlerseiten.
  Fehler behalten ihre HTTP-Statuscodes; Health und bisherige JSON-Fehler
  bleiben kompatibel. Jinja2 escaped dynamische Templatewerte automatisch.
- `frontend/templates/`: deutsche semantische Oberfläche, aktive Navigation,
  Tastatur-Sprunglink, eindeutige Platzhalter „In Vorbereitung“ ohne erfundene
  Kontostände, Buchungen oder andere persönliche Beispieldaten.
- `frontend/static/`: responsive CSS-Layouts, automatisches Hell-/Dunkel-Theme
  über `prefers-color-scheme`, lokale SVG-Icons; keine JavaScript-, CDN- oder
  Font-Abhängigkeit im Browser.
- Lokale URLs aus App-Routen und vertrauenswürdigem ASGI-`root_path`. Keine
  ungeprüfte Übernahme von Ingress-/Forwarded-Präfix-Headern.
- `tests/test_ui.py`: 22 neue API-Fälle, darunter echte ASGI-Mounts, fehlende
  Assets, 404/405, ignorierte Header und beide möglichen ASGI-Pfadvarianten.
- `browser_tests/`: 18 Playwright-Tests mit echtem HTTP-Server und Chromium,
  getrennt von der ohne Browser ausführbaren API-Suite.
- `pyproject.toml`, `uv.lock`: Jinja2 **3.1.6**, transitive Abhängigkeiten und
  separate Testgruppe mit Playwright **1.65.2** exakt festgehalten.
- `README.md`, `docs/DEVELOPMENT.md`, Etappenplan und dieser Fortschrittsbericht
  aktualisiert. Keine Finanzlogik, Datenbank, HA-Verpackung oder Authentifizierung
  aus späteren Etappen vorgezogen.

### Ausgeführte Tests und behobene Fehler

Linux x86_64, Python **3.12.14**, uv **0.13.6**, Chromium **156.0.8078.79**.
Alle Testanfragen und Mount-Pfade sind synthetisch.

| Befehl / Prüfung | Tatsächliches Ergebnis |
|---|---|
| `uv run --locked pytest tests/test_ui.py` nach erstem UI-Schritt | **16 passed** (0,49 s) |
| `uv run --locked pytest` nach Präfixkorrekturen | **23 passed** (0,45 s), einschließlich aller 3 bisherigen Health-Tests |
| `uv run --locked pytest tests/test_ui.py` nach Asset-Fehlerkorrektur | **22 passed** (0,50 s) |
| `uv run --locked pytest` nach Asset-Fehlerkorrektur | **25 passed** (0,43 s), vollständige API-Regression |
| `LEBENSASSISTENT_CHROMIUM_EXECUTABLE=/usr/bin/chromium uv run --group browser --locked pytest browser_tests` | **18 passed** (41,76 s) |
| `uv sync --locked --group browser` mit separatem `UV_PROJECT_ENVIRONMENT` | Frische virtuelle Umgebung erfolgreich eingerichtet, 28 Pakete installiert |
| `LEBENSASSISTENT_CHROMIUM_EXECUTABLE=/usr/bin/chromium uv run --group browser --locked pytest tests browser_tests` in dieser Umgebung nach allen Korrekturen | **43 passed** (40,84 s), vollständige API-/Browser-Regression |
| `uv run --locked ruff check .` | **All checks passed!** |
| `uv run --locked ruff format --check .` | Erfolgreich nach automatischer Formatkorrektur |
| `uv lock --check` | Erfolgreich; Lockfile konsistent |
| `uv build --wheel --out-dir <temporäres Arbeitsverzeichnis>` und ZIP-Inhaltsprüfung | Wheel erfolgreich gebaut; alle vier HTML-Templates, CSS und SVG-Icon enthalten |
| Screenshots in Hell/Dunkel bei Desktop- und Mobilbreite visuell gelesen | Keine sichtbaren Layoutfehler gefunden |
| Unabhängiges Code-Review | Keine offenen Befunde nach den Präfixkorrekturen |
| `git diff --cached --check` | Erfolgreich; vorgemerkten Diff manuell geprüft |
| `uvx --from detect-secrets==1.5.0 detect-secrets scan --no-verify` | Keine Funde in den vorgemerkten bzw. bereits versionierten Dateien |

Die 18 Browserfälle umfassen **320/390/768/1280 Pixel × hell/dunkel × ohne/mit
synthetischem Präfix** (16 Kombinationen) sowie zwei Prüfungen für 404-Rückweg
und Theme-Wechsel im Betrieb. Je Layoutfall werden alle acht Navigationsziele,
aktiver Navigationszustand, Tastatur-Sprunglink, Seitenoverflow und
Asset-/Konsolenfehler geprüft. Externe Browseranfragen würden blockiert und den
Test fehlschlagen lassen; es trat keine auf.

Tests wurden vor den Seitenrouten angelegt; der erste neue Test scheiterte wie
erwartet an HTTP 404 statt 200. Der erste Browsertestlauf fand anschließend
einen echten Fehler: `Request.url_for` wählte bei mehreren Mounts mit denselben
Routennamen das Präfix der falschen App. Das Review fand zusätzlich einen
Health-Fehler bei gesetztem `root_path` und bereits abgeschnittenem Requestpfad.
Beide Fälle wurden zuerst mit gezielt fehlschlagenden Tests nachgestellt und
danach behoben. Das abschließende Review fand einen dritten Pfadfehler:
Bei direkt angefragten fehlenden Assets wurde der zusätzliche StaticFiles-
Mount als Teil des App-Präfixes verwendet. Asset-Fehler bleiben nun unabhängig
vom Accept-Header JSON-Fehler; auch dieser Fall wurde erst mit zwei roten
Regressionstests nachgestellt und dann behoben. Die abschließenden Läufe
enthalten alle Korrekturen. Lint-/Formatfehler wurden ebenfalls vor Abschluss
beseitigt.

### Datenschutz

Vorgemerkte Änderungen manuell geprüft und automatisierten Secret-Scan ohne
externe Verifikation ausgeführt. Keine persönlichen Daten, Zugangsdaten,
Laufzeitdatenbanken oder Backups hinzugefügt. Browserbilder, Serverlogs,
Wheel, zusätzliche virtuelle Umgebung und Scanprotokoll liegen außerhalb des
Repositorys im temporären Arbeitsbereich. Die App benötigt zur Laufzeit keine
externen Dienste; die Installation von Entwicklungswerkzeugen und Browser
benötigt einmalig Paketdownloads.

### Grenzen und nächster Schritt

Die Modulansichten sind Platzhalter, noch keine nutzbare Finanz-/Projekt- oder
Terminverwaltung. Theme-Anpassung an die Browser-/Systemeinstellung wurde
getestet; eine separate manuelle HA-Theme-Einstellung wurde nicht synchronisiert.
**HA OS, echte Ingress-Authentifizierung, ARM/Raspberry Pi und Safari/iOS wurden
nicht getestet.** Die lokalen Mount-Tests belegen ausschließlich die geprüften
Pfadfälle. Es bleiben keine bekannten Fehler innerhalb von Etappe 0.2.

### Abschlusscheckliste

- [x] Etappe 0.2 implementiert.
- [x] API-, Browser- und Regressionstests lokal tatsächlich ausgeführt.
- [ ] HA-Laufzeittest (ausstehend).
- [ ] Nutzerfreigabe für Etappe 0.3.

# Entwicklungsfortschritt

## Stand
- Status: **Etappen 0.1 bis 0.4 und 1.1 lokal implementiert und geprüft**, App-Version **0.0.4** mit Korrektur des gemeldeten Formular-403; Freigabepause.
- Aktiver Branch: `alpha`; `main` nur Platzhalter, nicht bearbeiten.
- Zuletzt lokal abgeschlossene Etappe: **1.1** — bedienbare Konten-/Kategorienmasken, Archivierung/Aktivierung und Audit.
- Geprüft: **220 Tests** in frischer Umgebung: 187 Unit-/API-, 28 Chromium-Browser- und 5 echte Docker-Prüfungen. Container nach behobenem lokalem Speicherplatzfehler separat erfolgreich wiederholt; Lint/Format und Lockfile grün.
- Vom Nutzer bestätigt: Installation und erste Sichtprüfung von **0.0.1** auf seinem Home Assistant. Gerät, Architektur und HA-Version wurden nicht genannt.
- Nutzerrückmeldung: 403 bei Kontenanlage im normalen Browser, auch nach frischem Öffnen; lokal unter HA-Referrer-Policy reproduziert und korrigiert.
- Noch nicht geprüft: Korrektur und Update auf **0.0.4** auf HA, vollständige HA-Ingress-Session-/Restart-Prüfung, AppArmor-Einbindung und ARM-/Raspberry-Pi-Nachweis.
- Nächster Schritt: **Explizite Nutzerfreigabe für Etappe 1.2 abwarten**; noch keine Einnahmen-/Ausgabenbuchungen oder Transfers begonnen.

## Etappenlog
| Etappe | Status | Tests | Freigabe |
|---|---|---|---|
| 0.1 Grundgerüst und Health | Lokal abgeschlossen | 3 API-Tests grün; weiterhin Teil der Regression | Fortsetzung mit „weiter“ freigegeben |
| 0.2 Responsive UI | Lokal abgeschlossen | 25 API-Tests und 18 Browsertests grün; weiterhin Teil der Regression | Fortsetzung mit „weiter“ freigegeben |
| 0.3 HA-App/Ingress | Lokal abgeschlossen; Installation/Sichtprüfung von 0.0.1 auf HA bestätigt | 81 Tests grün, amd64-Build und lokaler Container-Lebenszyklus geprüft; weitere HA-/ARM-Prüfungen offen | Fortsetzung durch Nutzer freigegeben |
| 0.4 SQLite/Migration | Lokal abgeschlossen | 111 Tests grün; weiterhin Teil der Regression | Fortsetzung durch Nutzer freigegeben |
| 1.1 Konten/Kategorien | Lokal abgeschlossen | 212 Tests grün; erste Masken im Browser und Container geprüft | Ergebnis zur Abnahme vorgelegt |
| 1.1 Korrektur 0.0.4 | Gemeldeten Formular-403 lokal reproduziert und behoben | 220 Tests grün; native Browser-POSTs unter HA-Referrer-Policy geprüft | HA-Bestätigung der Korrektur ausstehend |
| 1.2–7.x | Offen | — | Ausstehend |

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

### Commitnachweis

Implementierung, Tests und Prüfprotokoll sind auf `alpha` im Commit
[`1d5b0d4bc2c9c208177dfa0e0d0cd1537c63028c`](https://github.com/karst3nl/homeassistant-lebensassistent/commit/1d5b0d4bc2c9c208177dfa0e0d0cd1537c63028c)
(`feat: add stage 0.2 responsive UI and prefix-safe navigation`) enthalten.
Der anschließende Dokumentationscommit ergänzt ausschließlich diesen
Hashnachweis; Anwendungs- und Testcode entsprechen dem mit 43 Tests geprüften
Stand.

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
- [x] Nutzerfreigabe für Etappe 0.3 durch „weiter“ (2026-11-14).

## Etappe 0.3 — 2026-11-14

### Freigabe und Umfang

Der Nutzer hat nach dem Abschlussbericht zu 0.2 mit **„weiter“** die nächste
Etappe freigegeben und die laufende Arbeit nochmals mit „mache weiter“
bestätigt. Ausschließlich 0.3 wurde umgesetzt; Ausgangscommit auf `alpha`:
`9fb4328e56a455d927d1dc1f90db28f6ec1f57ca`.

### Änderungen

- `config.yaml`, `repository.yaml`: experimentelle HA-App am Repository-Root,
  Ingress-Port 8099, manueller Start als Vorgabe, leere Optionen. Keine
  Hostports, zusätzlichen API-Rechte, Geräte oder Host-Verzeichnismounts.
  Als Zielarchitekturen sind amd64 und aarch64 konfiguriert; getestet wurde
  ausschließlich amd64. HA stellt den privaten `/data`-Mount automatisch bereit.
- `Dockerfile`, `.dockerignore`: mehrstufiger Build mit exakt gepinnten
  Multiarch-Index-Digests für Python 3.12.14 und uv 0.13.6. Nur Paketquellen
  und gesperrte Build-Eingaben gelangen in den Kontext; final wird eine nicht
  editierbare virtuelle Umgebung ohne Dev-/Browser-Werkzeuge übernommen.
- `integrations/homeassistant/ingress.py`: echter TCP-Peer wird vor allen
  Headern geprüft. Nur `172.30.32.2` ist erlaubt. Genau ein streng validierter
  `X-Ingress-Path` setzt das Präfix pro Anfrage. Forwarded-/User-Header ersetzen
  keine Authentifizierung. Redirects bleiben originrelativ; Präfix und Query
  bleiben erhalten. Direkte Zugriffe liefern 403, auch auf `/health`.
- `runtime.py`, `__main__.py`: fester Container-Einstieg, nur `/data` selbst
  wird vorbereitet (UID/GID 1000, Modus 0700). Danach Gruppen/GID/UID absenken,
  Schreibprobe mit exklusiver temporärer Datei, erst dann Uvicorn starten.
  `umask(0o077)`, `proxy_headers=False`, Access-Logs aus. Keine bestehenden
  Daten löschen oder rekursiv umstellen; keine Datenbank angelegt.
- `tests/test_ingress.py`, `test_addon_runtime.py`, `test_addon_config.py`:
  35 neue Unit-/API-Fälle. PyYAML **6.0.3** nur für Entwicklungstests ergänzt
  und mit `uv.lock` exakt festgehalten.
- `container_tests/`: echter Build, isoliertes Netz mit erlaubtem und fremdem
  TCP-Peer, Prozess-/Datenrechte sowie Stop/Start/Restart/Container-Neuerstellung.
  Nur UUID-benannte eigene Ressourcen werden angelegt und entfernt.
- `DOCS.md`, `CHANGELOG.md`, README, Entwicklungsanleitung und Etappenstatus
  aktualisiert. HA-Installationsanleitung verwendet ausdrücklich **`#alpha`**.

### Tatsächlich ausgeführte Prüfungen

Linux x86_64, Python **3.12.14**, uv **0.13.6**, Docker **29.9.2**, BuildKit
**0.34.0**, Chromium **156.0.8078.79**. Es wurden ausschließlich synthetische
Anfragen, Identitäten, Pfade und ein synthetischer Persistenzmarker verwendet.

| Befehl / Prüfung | Tatsächliches Ergebnis |
|---|---|
| `uv run --locked pytest tests/test_ingress.py` | **28 passed** (0,39 s) |
| `uv run --locked pytest tests/test_addon_runtime.py` | **5 passed** (0,28 s) |
| `uv run --locked pytest tests/test_addon_config.py` | **2 passed** (0,02 s) |
| `uv run --locked pytest` | **60 passed** (0,59 s), alle bisherigen API-Tests enthalten |
| `docker buildx imagetools inspect` für beide gepinnten Basisimages | Registry-Indizes mit amd64- und arm64-Manifesten vorhanden; keine ARM-Ausführung daraus abgeleitet |
| `docker build --progress=plain ...` ohne zusätzlichen Cloud-CA-Trust | Paketdownload scheiterte mit **UnknownIssuer** am Cloud-TLS-Proxy; kein erfolgreicher Build behauptet |
| Derselbe Build mit temporärer Dockerfile-Kopie, BuildKit-CA-Secret und `SSL_CERT_FILE` | Image auf **amd64 erfolgreich gebaut**; CA nicht in Image-Layer kopiert, TLS-Prüfung aktiv |
| `LEBENSASSISTENT_BUILD_CA_FILE=/etc/ssl/certs/ca-certificates.crt uv run --locked pytest container_tests` | **3 passed** (15,41 s); anschließend um Nachweis für standalone `uv`/`uvx` ergänzt |
| `uv sync --locked --group browser` mit separatem `UV_PROJECT_ENVIRONMENT` | Frische Umgebung erfolgreich eingerichtet; 29 Pakete installiert |
| `uv run --group browser --locked pytest tests browser_tests container_tests` mit vorhandenem Chromium und CA-Bundle in dieser Umgebung | **81 passed** (63,66 s): 60 API + 18 Browser + 3 Container, inklusive aller Nachweisergänzungen |
| `uv run --locked ruff check .` | **All checks passed!** |
| `uv run --locked ruff format --check .` | Erfolgreich; keine ausstehenden Formatänderungen |
| `uv lock --check`, `git diff --cached --check` | Erfolgreich |
| Unabhängiges Code-/Konfigurations-/Dokumentationsreview | Keine offenen Befunde; Nachweislücke für standalone uv/uvx ergänzt |
| `uvx --from detect-secrets==1.5.0 detect-secrets scan --no-verify` | Keine Funde in vorgemerkten oder bereits versionierten Dateien |

Die vollständigen Befehle und Umgebungsvariablen stehen in
[DEVELOPMENT.md](DEVELOPMENT.md). Der verwendete CA-Trust wird ausschließlich
als BuildKit-Secret in einer temporären Dockerfile-Kopie eingebunden. Die
versionierte Dockerfile wurde dafür nicht verändert; das finale Runtime-Image enthält
weder die CA-Datei noch uv/uvx, pytest oder Playwright.

Die drei Containerfälle belegen tatsächliche HTTP-200-Antworten vom
simulierten Supervisor, HTTP 400 bei fehlendem Präfix und HTTP 403 vom fremden
Peer trotz gefälschtem `X-Forwarded-For`. Präfixe und Redirects wurden geprüft.
PID 1 läuft mit UID/GID 1000; `/data` gehört 1000:1000 und hat Modus 0700.
Es gibt keine Port-Bindings. Nach geordnetem Stop, Start, Restart und kompletter
Neuerstellung des App-Containers war der synthetische Marker im selben Volume
weiter vorhanden. Ingress-Sessionpfade erschienen nicht in Access-Logs.

Die Containerprüfungen verwenden zusätzlich ein schreibgeschütztes
Root-Dateisystem, `no-new-privileges` und reduzierte Capabilities. Diese
verschärften Bedingungen wurden **lokal getestet**, aber nicht als
Supervisor-Laufzeiteinstellungen konfiguriert oder dort nachgewiesen.

Neue Tests wurden vor den jeweiligen Implementierungen angelegt und
scheiterten zunächst am fehlenden Adapter, Laufzeitmodul bzw. der fehlenden
App-Konfiguration. Die späteren grünen Läufe sind oben protokolliert.
Lint-/Formatfehler wurden innerhalb dieser Etappe behoben. Nach dem Review
wurde der Nachweis für standalone uv/uvx im Container-Test ergänzt; die finale
81er-Suite enthält diese zusätzliche Prüfung.

### Datenschutz und Grenzen

Vorgemerkten Diff manuell geprüft und automatisierten Secret-Scan ohne externe
Verifikation ausgeführt. Keine persönlichen Daten, Zugangsdaten, Datenbanken
oder Backups hinzugefügt. Build-/Serverlogs, Testvolumes, frische Umgebung und
Scanprotokoll liegen außerhalb des Repositorys; eigene Testcontainer, -netze,
-volumes und -imagetags werden vom Test wieder entfernt. Es wurde kein Image
veröffentlicht und keine echte HA-Installation verändert.

**Zum Abschluss dieser Etappe noch nicht durchgeführt:** Installation und Start/Stop/Restart auf HA OS, echte
HA-Login-/Logout- und Ingress-Sessionprüfung, Supervisor-AppArmor-Einbindung,
ARM-Build und Raspberry-Pi-Laufzeittest. Der verfügbare BuildKit-Worker bietet
nur amd64 an; es wurde kein privilegierter ARM-Emulator installiert. Die
lokalen Container sind ein synthetischer Netzwerktest, kein Home Assistant.
Die spätere Nutzerbestätigung für Installation/Sichtprüfung von 0.0.1 ist im
Abschnitt 0.4 protokolliert und ersetzt keine vollständige HA-Abnahme.

Die offene HA-/ARM-Abnahme ist in [DOCS.md](../DOCS.md) beschrieben. Es bleiben
keine bekannten Fehler innerhalb des lokal geprüften Umfangs von 0.3. Keine
Datenbank, Migration oder Finanzfunktion aus Etappe 0.4 oder später begonnen.

### Commitnachweis

Implementierung, Tests und Prüfprotokoll sind auf `alpha` im Commit
[`23be23e1ff62ff93f37219e067415ace68b6ae52`](https://github.com/karst3nl/homeassistant-lebensassistent/commit/23be23e1ff62ff93f37219e067415ace68b6ae52)
(`feat: package stage 0.3 HA app with protected ingress`) enthalten.
Der anschließende Dokumentationscommit ergänzt ausschließlich diesen
Hashnachweis; Anwendungs- und Testcode entsprechen dem mit 81 Tests geprüften
Stand.

### Abschlusscheckliste

- [x] Etappe 0.3 implementiert.
- [x] Unit-/API-, Browser- und echte Containerprüfungen lokal ausgeführt.
- [ ] HA-OS-/Ingress-/ARM-Laufzeittest (ausstehend).
- [x] Nutzerfreigabe für Etappe 0.4 nach bestätigter HA-Installation (2026-11-14).

## Etappe 0.4 — 2026-11-14

### Freigabe und Nutzerprüfung

Der Nutzer meldete zur angebotenen Alpha **0.0.1**: „das klappt und sieht gut
aus“ und gab die weitere Entwicklung frei. Das wird als erfolgreiche
Installation und erste Sichtprüfung auf seinem Home Assistant erfasst, nicht
als Login-/Logout-, Restart-, AppArmor- oder ARM-Abnahme. Geräte-/HA-Version
und Architektur sind unbekannt. Das neue Update **0.0.2** wurde dort noch
nicht geprüft.

Ausgangscommit auf `alpha`:
`8008dce77cb3b7e5006d87611c6111c4fce28ab9`. Ausschließlich Etappe 0.4 wurde
umgesetzt. Für Konten und Kategorien aus 1.1 liegt noch keine separate
Etappenfreigabe vor.

### Änderungen

- `database/connection.py`: Dateipfad muss ausdrücklich und absolut angegeben
  werden. Jede Verbindung prüft Fremdschlüssel und WAL, setzt
  `synchronous=FULL` und einen Lock-Timeout von fünf Sekunden. Keine global
  geteilten Connections. Explizite `BEGIN IMMEDIATE`-/Commit-/Rollback-Grenzen;
  verschachtelte Transaktionen werden abgelehnt, Verbindungen sicher geschlossen.
- `database/migrations.py`: lückenlose Registry, Versionsname, SHA-256-Prüfsumme
  und UTC-Zeitpunkt. Alle anstehenden Statements, Versionsmarken und
  Migration-Audits laufen in einer gemeinsamen Transaktion. Kein
  `executescript()` und keine impliziten Zwischen-Commits. Fremdschlüsselprüfung
  vor Commit; unbekannte neuere oder veränderte Historien werden abgelehnt.
- Erste produktive Migration erzeugt nur `audit_log` mit Index und
  Änderungs-/Löschschutz; technische Historie in `schema_migrations`.
  Keine Konten-, Buchungs- oder anderen Fachtabellen vorgezogen.
- `database/audit.py`: parametrisierte Inserts, UTC-Zeitpunkte und gültige
  JSON-Snapshots ohne NaN/Infinity. Aktive Transaktion des Aufrufers zwingend;
  der Helfer committet nicht selbst. Audit und spätere Fachänderungen können
  dadurch gemeinsam zurückrollen. Schutz gilt gegen reguläres UPDATE/DELETE,
  nicht gegen administrative Manipulation der Datei.
- `database/__main__.py`: explizites lokales Initialisierungs-/Migrationstool.
- `main.py`: optionale DB-Injektion; Migration im Lifespan vor HTTP-Annahme.
  Beschädigte oder nicht unterstützte Dateien verhindern den Start, ohne sie
  durch eine leere Datei zu ersetzen. Standard-App ohne expliziten Pfad erzeugt
  keine Datenbank; lokaler Start optional über `LEBENSASSISTENT_DATA_DIR`.
- HA-Entrypoint verwendet fest **`/data/lebensassistent.sqlite3`**, nach
  Rechteabwurf und Schreibprobe. Lifespan explizit eingeschaltet.
- 29 neue Unit-/API-Tests und erweiterte Containerprüfungen mit echten
  DB-/Audit-Persistenzchecks. Sämtliche SQL-Testtabellen und Daten synthetisch.
- App-Konfiguration, Paket und Docker-Versionsdefault konsistent auf **0.0.2**
  erhöht; `uv.lock` aktualisiert, keine neue Laufzeitabhängigkeit (sqlite3-stdlib).
- README, HA-Updateanleitung, Changelog, Architektur und lokale Entwicklungs-
  sowie Testanleitung aktualisiert.

### Tatsächlich ausgeführte Prüfungen

Linux x86_64, Python **3.12.14**, lokale SQLite-Bibliothek **3.53.1**, uv
**0.13.6**, Chromium **156.0.8078.79**. Docker-Prüfungen verwenden weiterhin
den gepinnten Python-Container und das temporäre Cloud-CA-Secret aus 0.3.

| Befehl / Prüfung | Tatsächliches Ergebnis |
|---|---|
| `uv run --locked pytest tests/test_database.py` | **5 passed** (0,03 s) |
| `uv run --locked pytest tests/test_database.py tests/test_migrations.py tests/test_audit.py` | **22 passed** (0,11 s) |
| `uv run --locked pytest tests/test_database_startup.py` | **7 passed** (0,77 s) |
| `uv run --locked pytest` | **89 passed** (1,28 s), einschließlich aller bisherigen API-Tests |
| `LEBENSASSISTENT_BUILD_CA_FILE=/etc/ssl/certs/ca-certificates.crt uv run --locked pytest container_tests` | **4 passed** (25,10 s); aktuelles 0.0.2-Image gebaut und gestartet |
| `uv sync --locked --group browser` mit separatem `UV_PROJECT_ENVIRONMENT` | Frische Umgebung mit Version 0.0.2 und 29 Paketen eingerichtet |
| `uv run --group browser --locked pytest tests browser_tests container_tests` mit Chromium-/CA-Konfiguration in dieser Umgebung | **111 passed** (66,25 s): 89 API + 18 Browser + 4 Container |
| `uv run --locked ruff check .` | **All checks passed!** |
| `uv run --locked ruff format --check .` | Erfolgreich |
| `uv lock --check`, `git diff --check` | Erfolgreich |
| Unabhängiges Code-/Startup-/Container-/Dokumentationsreview | Keine offenen Befunde; FK-Fail-closed und präzise Beschreibung des lokalen Starttests ergänzt |
| `git diff --cached --check` und manuelle Diff-Prüfung | Erfolgreich; keine Datenbankdateien im Repository gefunden |
| `uvx --from detect-secrets==1.5.0 detect-secrets scan --no-verify` | Keine Funde in vorgemerkten oder bereits versionierten Dateien |

Geprüft wurden Fresh-DB, erneuter Start ohne doppelte Migration/Audits,
synthetische Upgrades mit Datenerhalt, vollständiger Rollback von DDL/DML/
Historie/Audit bei einem Fehler sowie anschließender erfolgreicher Upgrade-
Versuch. Neue/falsche Historien und geänderte Prüfsummen werden abgelehnt.
Fremdschlüsselverletzungen und Audit-Fehler rollen Transaktionen zurück;
Audit-Einträge lassen sich weder ändern noch löschen. Nicht endliche JSON-
Werte werden vor dem Schreiben abgelehnt. SQL-ähnlicher synthetischer Text
bleibt durch Parameterbindung ein Datenwert.

Der echte Containerlauf prüfte die DB unter `/data`: UID/GID 1000, Dateimodus
0600, WAL, Fremdschlüssel, `integrity_check=ok` und keine FK-Verletzungen.
Ein synthetischer Audit-Eintrag und die Migrationshistorie blieben über Stop,
Start, Restart und Container-Neuerstellung mit demselben Volume erhalten.
Die 18 Browsertests prüfen den bisherigen UI-Umfang unverändert mit.

Tests wurden vor Connection-, Migrations-/Audit- und Startup-Implementierung
angelegt und scheiterten zunächst an fehlenden Modulen bzw. noch fehlender
Pfadinjektion. Alle späteren Ergebnisse oben wurden tatsächlich ausgeführt.
Lint-/Formatfehler wurden in derselben Etappe beseitigt.

### Datenschutz und Grenzen

Alle SQLite-Testdateien liegen in temporären Verzeichnissen bzw. eigenen
Docker-Testvolumes außerhalb des Repositorys. Die lokale Anleitung setzt
`umask 077` und ein privates Verzeichnis mit Modus 0700 voraus. Keine echten
Finanzdaten, Konten, Tokens, DB-Dateien oder Backups wurden hinzugefügt.
Vorgemerkten Diff manuell und mit Secret-Scan ohne externe Verifikation
geprüft; keine Funde. Testvolumes und eigene Containerressourcen wurden nach
den Prüfungen entfernt.

Die neu gebaute Version 0.0.2 wurde lokal auf Start und Persistenz geprüft;
ein tatsächlicher Wechsel vom 0.0.1- zum 0.0.2-Image auf HA wurde nicht
ausgeführt. Ebenso offen: volle HA-Session-/Restart-/AppArmor-Abnahme,
ARM-/Raspberry-Pi-Nachweis und spätere Backup-/Restoreprüfungen.

Die Oberfläche enthält weiterhin Platzhalter. Diese Etappe schafft die
technische Grundlage; Etappe 1.1 bringt als Nächstes Konten und Kategorien.
Keine Finanzverwaltung oder zusätzlichen Funktionen aus späteren Etappen
begonnen. Keine bekannten Fehler im lokal geprüften Umfang von 0.4.

### Commitnachweis

Implementierung, Tests und Prüfprotokoll sind auf `alpha` im Commit
[`fa133bf821eb00464aefd86d97c77993a9ec65d8`](https://github.com/karst3nl/homeassistant-lebensassistent/commit/fa133bf821eb00464aefd86d97c77993a9ec65d8)
(`feat: add stage 0.4 SQLite migrations and atomic audit`) enthalten.
Der anschließende Dokumentationscommit ergänzt ausschließlich diesen
Hashnachweis; Anwendungs- und Testcode entsprechen dem mit 111 Tests geprüften
Stand.

### Abschlusscheckliste

- [x] Etappe 0.4 implementiert, Version 0.0.2 vorbereitet.
- [x] Unit-/API-, Browser-, Migrations- und echte Containerprüfungen ausgeführt.
- [x] Nutzerbestätigung für Installation/Sichtprüfung von 0.0.1 dokumentiert.
- [ ] HA-Update-/Restart-/Security-/ARM-Prüfung von 0.0.2 (ausstehend).
- [x] Nutzerfreigabe für Etappe 1.1 durch „ja los weiter“ (2026-11-14).

## Etappe 1.1 — 2026-11-14

### Freigabe und Umfang

Der Nutzer hat nach dem Abschlussbericht zu 0.4 mit **„ja los weiter“** die
Etappe 1.1 freigegeben. Ausgangscommit auf `alpha`:
`df695f3023552f25293cc343b689d661c826ca06`.

Version **0.0.3** enthält erstmals bedienbare Konten-/Kategorienmasken unter
**Konten & Buchungen**. Keine Buchungen, Transfers, laufende Saldenberechnung
oder weiteren Funktionen aus 1.2 und später vorgezogen. Die HA-Bestätigung
des Nutzers gilt unverändert nur für Installation/Sichtprüfung von 0.0.1.

### Änderungen

- Migration **2** ergänzt `accounts` und `categories` mit Constraints und
  Kategorien-FK. Migration 1 und ihre Prüfsumme bleiben unverändert.
- `services/values.py`: Eurotext ohne Float in Integer-Cent umwandeln; Komma
  oder Punkt, maximal zwei Nachkommastellen, signierte int64-Grenzen. Echte
  ISO-Kalenderdaten ohne unbegründete Zukunftsgrenze prüfen.
- `services/catalog.py`: strikt validierte Konto-/Kategorieneingaben. Konten
  mit Name, Art, Anfangssaldo/-datum und optionaler Notiz anlegen, archivieren
  und wieder aktivieren. Negative Anfangssalden zulässig. Keine normale
  Änderung von Anfangssaldo/-datum nach Anlage, keine Löschung.
- Kategorien für Einnahme/Ausgabe, optional aktive Oberkategorie derselben
  Art. Aktive Kinder verhindern eine Elternarchivierung; Reaktivierung eines
  Kindes setzt aktive Eltern voraus. Keine Eltern-/Art-Bearbeitung und damit
  keine neuen Zyklen durch Umhängung.
- `repositories/catalog.py`: parametrisierter SQL-Zugriff. Änderung und Audit
  laufen in derselben `BEGIN IMMEDIATE`-Transaktion; ein Auditfehler rollt die
  Anlage vollständig zurück. Wiederholter Status erzeugt keine Audit-Duplikate.
- `api/catalog.py`, `forms.py`, `views.py`, `ui.py`: servergerenderte Formulare
  ohne JavaScript und ohne zusätzliche JSON-API. Pflicht-CSRF-Token pro App-
  Instanz, konstantzeitlicher Vergleich vor Service-/DB-Aufruf, ergänzende
  Fetch-Site-/Origin-Authority-Prüfung. URL-Formulare auf 32 KiB/16 eindeutige
  Felder begrenzt; falsches Encoding, doppelte/unerwartete Felder abgewiesen.
- Ingress-Marker erst nach tatsächlicher Peer-/Präfixprüfung. Nur dann kann
  ein einzelner gültiger X-Forwarded-Host als zusätzliche Authority dienen.
  Kein globales Scheme-Vertrauen in X-Forwarded-Proto; `proxy_headers=False`
  bleibt erhalten. Authority-Prüfung ist kein vollständiger Scheme-/Origin-
  Abgleich und ersetzt den CSRF-Token nicht.
- `accounts.html`, CSS und Startseitenstatus: deutsche responsive Masken mit
  Fehlermeldungen, Werterhalt, Archivstatus, EUR-/Datumsdarstellung und lokalen
  Formularpfaden. Anfangssalden als solche bezeichnet, nicht als gebuchte
  Kontostände. Finanz-/Formularseiten `Cache-Control: no-store`, Jinja-Escaping.
- `main.py` sowie Ingress-/Testharness-Anbindung erweitert. Gemountete Browser-
  Test-Apps starten ihre eigenen DB-Lifespans explizit; Daten nur in privaten
  temporären Verzeichnissen. Keine DB im Repository.
- Version in HA-Konfiguration, Paket und Docker-Default auf **0.0.3** erhöht.
  Pydantic **2.14.3** nun direkt/exakt deklariert (bereits vorher als Laufzeit-
  Abhängigkeit vorhanden), `uv.lock` aktualisiert.
- README, Changelog, HA-Bedien-/Updateanleitung, Architektur und lokale
  Entwicklungs-/Testbefehle aktualisiert. Keine produktiven Beispieldaten.

### Tatsächlich ausgeführte Prüfungen

Linux x86_64, Python **3.12.14**, uv **0.13.6**, Chromium **156.0.8078.79**.
Alle Konten, Kategorien, Namen, Beträge, Notizen und Netzwerkdaten in Tests
sind synthetisch. Docker verwendet wie zuvor das temporäre CA-Secret ohne
Kopie der Cloud-CA in das Runtime-Image.

| Befehl / Prüfung | Tatsächliches Ergebnis |
|---|---|
| `uv run --locked pytest tests/test_catalog_values.py` | **25 passed** (0,03 s) |
| `uv run --locked pytest tests/test_catalog_service.py` | **19 passed** (0,14 s) |
| `uv run --locked pytest tests/test_catalog_http.py` nach Präfix-Fixture-Korrektur | **27 passed** (0,70 s) |
| Derselbe HTTP-Befehl nach Authority-/Body-/Datums-Grenzfällen | **47 passed** (1,09 s) |
| `uv run --locked pytest` | **180 passed** (2,02 s), alle bisherigen Unit-/API-Fälle enthalten |
| `LEBENSASSISTENT_CHROMIUM_EXECUTABLE=/usr/bin/chromium uv run --group browser --locked pytest browser_tests` | **27 passed** (52,18 s) |
| `LEBENSASSISTENT_BUILD_CA_FILE=/etc/ssl/certs/ca-certificates.crt uv run --locked pytest container_tests` | **5 passed** (34,72 s), danach zusätzliche Log-/Neuerstellungsnachweise ergänzt |
| `uv sync --locked --group browser` mit separatem `UV_PROJECT_ENVIRONMENT` | Frische Umgebung mit Version 0.0.3 und 29 Paketen erfolgreich eingerichtet |
| `uv run --group browser --locked pytest tests browser_tests container_tests` mit Chromium-/CA-Konfiguration in dieser Umgebung | **212 passed** (89,27 s): 180 API + 27 Browser + 5 Container, einschließlich aller Ergänzungen |
| `uv run --locked ruff check .`, `ruff format --check .`, `uv lock --check`, `git diff --check` | Erfolgreich |
| Visuelle Prüfung der Browserbilder | Mobil hell und Desktop dunkel geprüft; Formulare und Datensätze ohne Seitenoverflow |
| Unabhängiges Backend-/Schema-/Formular-/CSRF-/Dokumentationsreview | Keine offenen Befunde; Port-0- und Jahresdarstellungsrandfall korrigiert |

Die 25 Wertetests prüfen negative und beide int64-Grenzsalden, ungültige
Dezimalformen/Exponenten/NaN/Infinity und Kalenderdaten. 19 Servicetests prüfen
Anlage, Archivierung/Aktivierung, unveränderte Anfangssalden, Kategorienregeln,
Audit-Rollback und Upgrade mit erhaltener v1-Historie. Die ursprünglichen v1-
Migration-/Audit-Regressionen bleiben mit expliziter v1-Registry erhalten.

47 HTTP-Fälle prüfen Root/Präfix, Fehlermeldungen, Werterhalt, HTML-Escaping,
fehlende/falsche CSRF-Tokens, fremde/malformed Authority, Port 0, JSON-/Body-
Encoding, Größe, doppelte Felder und das Jahr 0001 mit vierstelliger Anzeige.
Unautorisierte oder ungültige Anfragen erzeugen keine Konto-/Auditänderung.

Neun neue Browserfälle umfassen acht vollständige Formularabläufe bei
390/1280 Pixeln × hell/dunkel × ohne/mit Präfix und einen XSS-Fall. Sie prüfen
echte POSTs, Fehlerkorrektur, Cent-/Datumsanzeige, Archivierung/Aktivierung,
Reload und Skript-Nichtausführung. Die 18 bisherigen Layout-/Navigationstests
bei 320/390/768/1280 Pixeln bleiben ebenfalls grün.

Das echte Containernetz prüft erlaubte POSTs vom simulierten Supervisor und
403 bei Peer-Fälschung oder falschem/über Neustart veraltetem Token. Vor Start
wird mit dem aktuellen Test-Image synthetisch Schema 1 mit einem Test-Audit
erzeugt; der App-Start migriert auf Schema 2 und erhält diese Historie. Das
belegt ein Schema-Upgrade, keinen tatsächlichen Wechsel alter/neuer Images.
Neu angelegte Konten/Kategorien und Anfangssalden bleiben nach Restart und
kompletter Neuerstellung mit demselben Volume erhalten. Namen und CSRF-Token
erscheinen nicht in Standardlogs.

### Behobene Fehler und Abgrenzung

Neue Wert-/Service-/HTTP-Tests wurden vor ihren Implementierungen angelegt
und zunächst erwartungsgemäß rot ausgeführt. Nach Erweiterung auf Schema 2
wurden die historischen v1-Test-Fixtures explizit auf v1 begrenzt; neue
Produktivtests prüfen Schema 2. Im ersten HTTP-Lauf fehlte bei 13 Präfixfällen
die Child-App-Initialisierung im Test-Mount; der Testharness führt die Child-
Lifespans nun korrekt aus. Danach liefen alle Root-/Präfixfälle grün.

Die ergänzende Authority-Prüfung behandelte anfangs Port 0 durch einen `or`-
Default wie den Standardport; explizite None-Prüfung und Bereichscheck beheben
das. Der verpflichtende Token blieb auch vorher unverändert erforderlich.
`strftime` wurde für vierstellige Jahre durch explizite Formatierung ersetzt.
Beide Randfälle sind durch HTTP-Tests abgesichert. Lint-/Formatfehler wurden
in derselben Etappe beseitigt.

**Nicht durchgeführt:** HA-Update/Bedienprüfung von 0.0.3, vollständige HA-
Login-/Logout-/Restart-/AppArmor-Abnahme, ARM-/Raspberry-Pi- und Safari/iOS-
Prüfungen. Die Nutzerbestätigung bezieht sich nur auf 0.0.1. Keine Einnahmen,
Ausgaben, Transfers, Budgets oder weiteren Module aus Folgeetappen begonnen.

### Datenschutz und Abschlussprüfung

Vorgemerkten Diff manuell geprüft und `detect-secrets==1.5.0 scan --no-verify`
ausgeführt: **keine Funde**. Keine persönlichen Finanzdaten, Zugangsdaten,
Laufzeitdatenbanken oder Backups im Repository. Die Tokens in Tests werden
jeweils synthetisch zur Laufzeit erzeugt. Screenshots, Scanprotokoll, frische
Umgebung und SQLite-Testdateien liegen außerhalb des Repositorys. Eigene
Docker-Testcontainer, -volumes und -netze sind nach den Tests entfernt;
die abschließende Ressourcenprüfung fand keine verbliebenen Testressourcen.
`git diff --cached --check` ist grün. Keine bekannten offenen Fehler im lokal
geprüften Umfang von Etappe 1.1.

### Commitnachweis

Implementierung, Tests und Prüfprotokoll sind auf `alpha` im Commit
[`8e15eda8e47ab2ce642164f8b97767408caa7d7a`](https://github.com/karst3nl/homeassistant-lebensassistent/commit/8e15eda8e47ab2ce642164f8b97767408caa7d7a)
(`feat: add stage 1.1 accounts and categories`) enthalten.
Der anschließende Dokumentationscommit ergänzt ausschließlich diesen
Hashnachweis; Anwendungs- und Testcode entsprechen dem mit 212 Tests geprüften
Stand.

### Abschlusscheckliste

- [x] Etappe 1.1 implementiert, Version 0.0.3 mit ersten bedienbaren Masken.
- [x] Unit-/API-, Browser-, Migrations- und echte Containerprüfungen ausgeführt.
- [ ] HA-Update-/Bedien-/Security-/ARM-Prüfung von 0.0.3 (ausstehend).
- [ ] Nutzerfreigabe für Etappe 1.2.

## Etappe 1.1 — Korrektur des Formular-403, Version 0.0.4 — 2026-11-14

### Nutzerrückmeldung und Ursache

Der Nutzer meldet einen 403 beim Kontoanlegen, auch nach erneutem Öffnen der
Weboberfläche im normalen Browser. Das ist ein Fehler in der abgeschlossenen
Etappe 1.1; keine Freigabe oder Umsetzung von Etappe 1.2. Ausgangscommit:
`ae71e86864b09172462f1172a8f295d18aa33b33` auf `alpha`.

Die [globale HA-Core-Antwortmiddleware](https://github.com/home-assistant/core/blob/dev/homeassistant/components/http/headers.py)
setzt `Referrer-Policy: no-referrer`. Im echten Chromium lässt sich damit bei
nativen Formular-POSTs `Origin: null` reproduzieren. Core und Supervisor reichen
diesen Request-Header weiter. Die bisherige ergänzende Origin-Prüfung lehnte
ihn trotz gültigem CSRF-Token ab. Die bisherigen Browser-/Container-Fixtures
simulierten diese Antwortpolicy nicht und hatten den Fehler nicht erfasst.

### Änderungen und unveränderte Fachregeln

- `api/forms.py`: exakt einen Origin-Wert `null` ausschließlich nach
  erfolgreicher Ingress-Peer-/Präfixprüfung und gültigem Pflicht-CSRF-Token
  zulassen. Fetch-Site wird weiterhin vorher geprüft. Lokale Null-Origins,
  doppelte Origins, fremde Peers und fehlende/falsche Tokens bleiben gesperrt.
  Weder Referrer-Policy noch Produktions-Peer-Gate werden abgeschwächt.
- `tests/test_catalog_http.py`: sieben zusätzliche Fälle für alle vier
  Formularrouten sowie Token-/Fetch-Site-/Origin-/Peer-Angriffe ohne DB- oder
  Auditänderung. Bestehende lokale Null-Origin-Abweisung bleibt Teil der Suite.
- `browser_tests/server.py`, `test_ingress_forms_browser.py`: eigene temporäre
  Ingress-Testdatenbank und Testadapter mit HA-Antwortpolicy. Echtes iframe,
  sechs native POSTs für Konto/Kategorie anlegen, archivieren und aktivieren;
  Origin wird vom Browser erzeugt, nicht im Test überschrieben. Peer-Simulation
  ausschließlich im Testserver, kein Nachweis einer echten HA-Anmeldung.
- `container_tests/test_container.py`: echte TCP-POSTs mit Null-Origin;
  falscher Token, Cross-Site und gefälschter Peer weiterhin 403. Restart und
  Container-Neuerstellung erhalten synthetische Konten und Kategorien.
- `config.yaml`, `pyproject.toml`, `Dockerfile`, `uv.lock`: Version **0.0.4**;
  keine neuen Pakete oder Migrationen. Schema 2 und Anfangssaldo-Regeln bleiben
  erhalten. Changelog, README, HA-Updateanleitung, Architektur, Testanleitung
  und Etappenstatus aktualisiert.

### Tatsächlich ausgeführte Prüfungen

Linux x86_64, Python 3.12.14, uv 0.13.6, Chromium 156.0.8078.79; ausschließlich
synthetische Daten. Separate frische Umgebung über `UV_PROJECT_ENVIRONMENT`,
beschreibbarer `UV_CACHE_DIR`, Chromium-/Build-CA-Konfiguration wie oben.

| Befehl / Prüfung | Tatsächliches Ergebnis |
|---|---|
| `uv run --locked pytest tests/test_catalog_http.py -k 'no_referrer or null_origin'` vor Fix | **1 failed, 6 passed** (0,48 s); Kontoanlage 403 statt 303 reproduziert |
| `uv run --group browser --locked pytest browser_tests/test_ingress_forms_browser.py` vor Fix | **1 failed** (2,34 s); Browser-Origin `null` nachgewiesen, POST 403 statt 303 |
| `uv run --locked pytest tests/test_catalog_http.py` nach Fix | **54 passed** (1,41 s) |
| Neuer Browserfall nach Fix | **1 passed** (2,97 s); alle sechs nativen POSTs mit Null-Origin und 303 |
| `uv sync --locked --group browser` in frischer Umgebung | 29 Pakete einschließlich Version 0.0.4 installiert |
| `uv run --group browser --locked pytest tests browser_tests container_tests` | **215 passed, 5 errors** (70,61 s); alle API-/Browsertests grün, Container-Setup wegen Docker-Speicherplatzfehler blockiert |
| `uv run --group browser --locked pytest container_tests` nach gezielter Cachebereinigung | **5 passed** (32,16 s); damit alle **220 Tests** bestanden |
| Ruff check/format, `uv lock --check`, `git diff --cached --check` | Erfolgreich |
| Unabhängiges Code-/Security-Review, zusätzlicher HTTP-Testlauf | Keine offenen Befunde; nochmals **54 passed** (1,47 s) |
| `detect-secrets==1.5.0 scan --no-verify` und manuelle Diff-Prüfung | Keine Funde; keine DB-Dateien im Repository |

Docker meldete beim Containerstart ausdrücklich `no space left on device`.
Sechs einzeln identifizierte, ungenutzte Build-Cache-Einträge unserer früheren
Test-Builds wurden anhand ihrer IDs entfernt; keine pauschale Bereinigung.
Danach liefen die fünf Containerfälle mit unverändertem Anwendungscode grün.
Einzelne Formatfehler wurden vor der abschließenden Prüfung behoben.

### Datenschutz, Grenzen und Abschluss

Keine privaten URLs, Tokens, Konten oder sonstigen Finanzdaten angefordert oder
hinzugefügt. Alle Testdaten, Testdatenbanken, Logs, Screenshots und Scanprotokolle
bleiben außerhalb des Repositorys. Die lokale Simulation belegt den Fehler
und die Korrektur unter der nachgebildeten HA-Antwortpolicy. **Die Bestätigung
der Korrektur auf dem Nutzer-HA, vollständige HA-Security-/Restart-/AppArmor-
Abnahme und ARM-/Raspberry-Pi-Prüfungen stehen weiterhin aus.** Keine bekannten
offenen Fehler im lokal geprüften Umfang dieser Korrektur.

- [x] Formular-403 lokal reproduziert und in Version 0.0.4 korrigiert.
- [x] Lokale Unit-/API-, Browser- und Containerregression tatsächlich ausgeführt.
- [ ] Bestätigung der Korrektur auf Home Assistant; weitere HA-/ARM-Abnahme.
- [ ] Nutzerfreigabe für Etappe 1.2.

# Development policy

## Branches

- `alpha` is the **only active development branch** until the full v1.0 application is complete and tested.
- `main` remains a minimal stable placeholder and must not receive development commits.
- Changes, tests and application docs are committed to `alpha`.
- After the release acceptance checklist has passed, merge `alpha` into `main` through a reviewed pull request. Never auto-merge.

## Privacy

- Use synthetic data only in tests, screenshots and documentation.
- Never commit real account balances, salaries, bank records, names, vehicle registration plates, API credentials, actual Home Assistant configuration or application databases.
- Review staged changes before each push. `.gitignore` is not sufficient protection for already tracked files.
- Runtime data must be stored in Home Assistant persistent storage, not in the repository.

## Scope

The intended app covers accounts and transactions, recurring expenses, savings goals, vehicle expenses and refuelling, projects, timesheets, notifications, and a configurable dashboard.

The functional specification must be sanitized before publishing, including examples and metadata.

## Lokale Entwicklung

### Voraussetzungen und Einrichtung

- Git, Python **3.12.14** und **uv 0.13.6** (getestete Werkzeugversionen).
- Bei Bedarf uv installieren: `python3 -m pip install --user "uv==0.13.6"`.
  Das Benutzer-Skriptverzeichnis muss im `PATH` stehen.
- Internetzugang für die erstmalige Installation der Entwicklungsabhängigkeiten.
  Der laufende Health-Endpunkt benötigt keine externen Dienste.

```sh
git clone --branch alpha --single-branch https://github.com/karst3nl/homeassistant-lebensassistent.git
cd homeassistant-lebensassistent
git branch --show-current
git status -sb
uv sync --locked
```

Der aktive Branch muss `alpha` sein. `.python-version` legt die Python-Version
fest; uv kann den Interpreter bei Bedarf herunterladen. `uv sync --locked`
erstellt `.venv`, installiert das lokale Paket und die Entwicklungswerkzeuge
und prüft, dass `pyproject.toml` und `uv.lock` übereinstimmen. Direkte
Abhängigkeiten sind exakt versioniert; `uv.lock` hält auch transitive Versionen
und Paket-Prüfsummen fest. Das Build-Backend ist ebenfalls exakt versioniert.
Die virtuelle Umgebung gehört nicht in Git.

### Lokal starten und stoppen

Im Repository-Verzeichnis:

```sh
uv run --locked uvicorn lebensassistent.main:app --host 127.0.0.1 --port 8000
```

In einem zweiten Terminal:

```sh
curl --fail-with-body http://127.0.0.1:8000/health
```

Erwartet: HTTP **200**, Content-Type `application/json`, Antwort
`{"status":"ok"}`. Der Endpunkt bestätigt ausschließlich, dass der Webserver
Anfragen verarbeitet. Datenbank- und Home-Assistant-Verbindungen werden nicht
geprüft. Mit `Strg+C` im Server-Terminal beenden.

Der Entwicklungsserver bindet nur an die lokale Loopback-Adresse. Ist Port
8000 belegt, Server und curl mit demselben anderen lokalen Port starten.
Die separate HA-/Ingress-Konfiguration aus Etappe 0.3 ist in
[DOCS.md](../DOCS.md) beschrieben. Der hier gestartete lokale Entwicklungsserver
hat keine HA-Anmeldung und bleibt ausschließlich auf Loopback.

Die Oberfläche ist unter **http://127.0.0.1:8000/** erreichbar. Sie bietet eine
Übersicht und sieben weitere navigierbare Modulbereiche. Unter „Konten &
Buchungen“ sind mit Datenbank Konten, Kategorien und Normalbuchungen bedienbar; die
übrigen Bereiche bleiben Platzhalter.
Alle Texte, Styles und Icons werden lokal ausgeliefert; JavaScript und externe
Fonts/CDNs sind nicht erforderlich. Die Navigation funktioniert auch mit
Tastatur und ohne JavaScript. Ein Sprunglink führt direkt zum Hauptinhalt.
Das Theme folgt automatisch der Browser-/Systemeinstellung
`prefers-color-scheme`. Die Synchronisierung mit einer abweichenden manuellen
HA-Theme-Einstellung ist noch nicht implementiert oder getestet.

### Lokaler Start mit Datenbank (Etappe 0.4)

Der normale Entwicklungsstart ohne Konfiguration bleibt ohne Datenbank.
Für Datenbanktests ausschließlich synthetische Daten in einem ausdrücklich
angelegten privaten Verzeichnis **außerhalb des Repositorys** verwenden:

```sh
umask 077
task_data_dir=$(mktemp -d)
uv run --locked python -m lebensassistent.database --path "$task_data_dir/lebensassistent.sqlite3"
LEBENSASSISTENT_DATA_DIR="$task_data_dir" uv run --locked uvicorn lebensassistent.main:app --host 127.0.0.1 --port 8000
```

`mktemp -d` erzeugt ein privates Verzeichnis mit Modus 0700; die gesetzte
umask schützt neue Dateien. Das temporäre Verzeichnis eignet sich nur für
synthetische Entwicklungsdaten. Für wiederholte lokale Sitzungen denselben
privaten Pfad ausdrücklich erneut verwenden. Der Pfad muss absolut sein;
fehlende Elternverzeichnisse werden nicht automatisch angelegt.

Der CLI-Befehl initialisiert oder aktualisiert die Datei und meldet aktuell
`Database ready; schema version 3`. Der Server führt dieselbe Prüfung vor dem
ersten HTTP-Zugriff erneut idempotent aus. In HA ist der Pfad unabhängig von
dieser Entwicklungsvariable fest auf `/data/lebensassistent.sqlite3` gesetzt.

Aktuell gibt es `schema_migrations`, `audit_log`, `accounts`, `categories`,
`transactions` und `transaction_splits`. Migrationen 1 und 2 bleiben unverändert;
Migration 3 ergänzt die Buchungstabellen. Neue Verbindungen
prüfen WAL und Fremdschlüssel, verwenden `synchronous=FULL` und einen
Lock-Timeout von fünf Sekunden. Schreibvorgänge verwenden explizite
Transaktionen; Audit-Einträge dürfen nur innerhalb derselben aktiven
Transaktion entstehen. Migrationen haben unveränderliche Prüfsummen und
werden gemeinsam mit ihrer Versionsmarke und ihrem Audit-Eintrag committed.

Bei beschädigten Dateien, nicht unterstützten neueren Versionshistorien oder
geänderten Migrationen bricht der Start ab. Es gibt keinen automatischen
Reset auf eine leere Datenbank. SQLite-UPDATE/DELETE auf Audit-Einträgen sind
gesperrt; das ist kein Schutz gegen administrativen Dateizugriff.

### Konten, Kategorien und Buchungen (bis Etappe 1.2, Version 0.0.5)

Mit dem oben konfigurierten Datenbankstart
**http://127.0.0.1:8000/bereiche/finanzen** öffnen. Dort lassen sich Konten und
Kategorien anlegen, archivieren und wieder aktivieren sowie Einnahmen und
Ausgaben erfassen. Die Testanleitung steht
in [DOCS.md](../DOCS.md). Ohne expliziten lokalen Datenpfad bleiben die
Schreibfunktionen nicht verfügbar; eine Repository-Datenbank wird nicht erzeugt.

Eurotext wird nur mit Integerarithmetik in Cent umgewandelt. Komma oder Punkt
als Dezimalzeichen, maximal zwei Nachkommastellen, keine Gruppierung oder
Exponenten. Beide signierten SQLite-int64-Grenzen und negative Anfangssalden
werden geprüft. Öffnungsdatum und Anfangssaldo sind nach Anlage nicht frei
änderbar. Normalbuchungen erhalten eine vollständige Kategoriezuordnung.
Betrag positiv, Kategorie passend und aktiv, Konto aktiv, Datum ab Kontoöffnung;
Datum standardmäßig heute in Europe/Berlin, Notiz optional. Buchung, Zuordnung
und Audit werden atomar gespeichert. Die technische eindeutige Formular-ID
verhindert doppelte Übermittlung; gleiche ID mit anderem Inhalt ergibt 409.

Aktuelle Kontosalden stammen ausschließlich aus Anfangssaldo und `posted`-
Bewegungen bis heute, berechnet mit Python-Integern aus einem SQL-Snapshot.
Zukünftige Datierungen sind sichtbar gekennzeichnet und zählen erst ab ihrem
Datum; vor Kontoöffnung kein Saldo. Archivierte Historie bleibt erhalten.
Die Liste zeigt die letzten 50 Einträge. Noch keine Mehrfachaufteilungen,
Transfers, Rückerstattungen oder Buchungsänderung/Stornierung.

Die Formulare verwenden normale HTML-POSTs, keinen JavaScript-Client und keine
zusätzliche JSON-API. Ein zufälliger CSRF-Token pro App-Instanz ist zwingend;
`compare_digest` prüft ihn vor Service-/DB-Aufrufen. Nach Neustart alte Seiten
neu laden. Finanzseiten und Formularantworten haben `Cache-Control: no-store`.
URL-kodierte Bodies sind auf 32 KiB und 16 eindeutige Felder begrenzt;
andere Encodings, doppelte oder unerwartete Felder werden abgewiesen.

Fetch-Site und die Origin-Authority werden zusätzlich geprüft. Nur nach der
Ingress-Peer-/Präfixprüfung darf ein einzelner gültiger X-Forwarded-Host als
zusätzliche Authority dienen. Kommagetrennte, doppelte und ungültige Angaben
werden dabei abgewiesen. Das ist kein vollständiger Scheme-/Origin-Abgleich
und ersetzt den CSRF-Token nicht. `proxy_headers=False` bleibt erhalten;
X-Forwarded-Proto schreibt das ASGI-Scheme nicht um.

HA versieht auch Ingress-Antworten mit `Referrer-Policy: no-referrer`.
Bei nativen Browser-POSTs entsteht dadurch `Origin: null`. Seit 0.0.4 ist genau
ein solcher Origin nur nach verifiziertem Ingress und gültiger Tokenprüfung
zulässig. Fetch-Site wird vorher geprüft; lokale Null-Origins, doppelte
Origin-Header, fremde Peers und fehlende/falsche Tokens bleiben abgewiesen.
Die Referrer-Policy wird nicht überschrieben oder abgeschwächt.

### Tests und Lint

```sh
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv lock --check
```

pytest prüft **270 Unit-/API-Tests ohne Browser oder Docker**:

- `GET /health`: HTTP 200, JSON-Content-Type und exakte Antwort.
- `POST /health` mit synthetischem Inhalt: HTTP 405; Health bleibt unverändert.
- Ein erfundener, unbekannter Pfad: HTTP 404.
- Deutsche HTML-Seiten und alle acht Navigationsziele.
- Lokale Asset-Pfade und Browser-Fehlerseiten mit korrektem HTTP 404/405.
- Präfixerhalt bei ASGI-Mounts und gesetztem `root_path`, einschließlich
  mehrerer App-Mounts; Health behält auch für Browser-Anfragen sein JSON.
- Fehlende/private Assets bleiben unerreichbar; ungeprüfte Ingress-/Proxy-
  Header verändern keine Links.
- Der HA-Adapter erlaubt nur den echten Supervisor-Peer; gefälschte Header,
  fehlende/doppelte/ungültige Präfixe und direkte Zugriffe werden abgelehnt.
- Private Datenpfad-Vorbereitung, Rechteabwurf und fehlgeschlagene
  Laufzeitvorbereitung werden mit temporären Verzeichnissen geprüft.
- Die App-Konfiguration beantragt weder Hostports noch zusätzliche API-,
  Geräte- oder Hostrechte.
- Fresh-DB, idempotenter Start, Upgrade mit Datenerhalt, atomarer DDL-/DML-
  Rollback, Versions-/Prüfsummenfehler, Fremdschlüssel und Audit-Rollback.
- Beschädigte oder neuere Datenbanken verhindern den Start; Standard-Imports
  erzeugen keine Repository-Datenbank. Der explizite lokale Datenpfad und das
  CLI-Migrationstool werden in eigenen Prozessen geprüft.
- Centkonvertierung, Datums-/int64-Grenzen, Kontenanlage, Archivierung und Audit
  in derselben Transaktion; bei Auditfehlern bleibt kein halber Datensatz.
- Kategorienhierarchie mit gleicher Art, aktiven Eltern und kontrollierter
  Archivierung; Upgrade von Schema 1 auf 2 mit erhaltener Audit-Historie.
- HTML-Formulare einschließlich Präfix, XSS-Escaping, CSRF-/Authority- und
  Body-/Encoding-Grenzfälle. Unzulässige Anfragen ändern keine Konten/Audits.
- HA-Formular-POSTs mit `Origin: null` nur hinter verifiziertem Ingress und
  gültigem Token; die Angriffsvarianten bleiben ohne DB-/Auditänderung.
- Normalbuchungen, vollständige Kategoriezuordnung, Audit-/Zuordnungsrollback,
  Upgrade von Schema 2 auf 3 mit Datenerhalt, Stichtag-/Archiv-/Zukunftssalden,
  Cent-Präzision und Aggregationen über den SQLite-int64-Bereich hinaus.
- Formular-Werterhalt, Schutz des neuen POSTs, Replay/Konflikte und parallele
  Übermittlung derselben Buchungsanfrage ohne Doppelanlage.

Die ursprünglichen Migration-1-/Audit-Grundlagentests laufen weiterhin mit
expliziter v1-Registry; separate Tests prüfen die neue produktive Registry.

Einzelne Bereiche lassen sich z. B. mit
`uv run --locked pytest tests/test_ingress.py` gezielt prüfen.

Die API-Tests verwenden isolierte App-Instanzen mit FastAPI-Testclient. Es werden
keine persönlichen Daten, Laufzeitdatenbanken oder laufenden HA-Systeme
benötigt. Warnungen sind in pytest als Fehler konfiguriert. Ein tatsächlicher
Serverstart mit curl ergänzt die API-Tests. Erfolgreiche lokale Prüfungen sind
keine Abnahme auf Home Assistant OS oder ARM/Raspberry Pi.

### Browsertests und vollständige Regression

Die zusätzliche Gruppe `browser` enthält exakt versioniertes Playwright.
Einmalig Browser und gegebenenfalls benötigte Systembibliotheken gemäß der
Playwright-Ausgabe einrichten:

```sh
uv sync --locked --group browser
uv run --group browser --locked playwright install chromium
```

```sh
uv run --group browser --locked pytest browser_tests
uv run --group browser --locked pytest tests browser_tests
```

Der erste Befehl führt **37 Browsertests** aus, der zweite die API-/Browser-
Suite mit **307 Tests**. Die Browserprüfungen starten selbst
einen lokalen Uvicorn-Prozess auf einem freien Loopback-Port und beenden ihn
anschließend. Sie prüfen 320/390/768/1280 Pixel, beide Themes, alle
Navigationsziele, Tastatur-Sprunglink, Seitenoverflow, Asset-/Konsolenfehler,
externe Anfragen sowie 404-Rücknavigation und einen Theme-Wechsel im Betrieb.
Zusätzlich werden acht vollständige Konten-/Kategorien-Formularabläufe bei
390/1280 Pixeln, hell/dunkel und mit/ohne Präfix sowie ein XSS-Fall geprüft.
Fehlerkorrektur, Centdarstellung, Archivierung/Aktivierung und Reload laufen
dabei im echten Browser. Eigene temporäre Datenbanken werden über die explizit
gestarteten Lifespans der gemounteten Apps initialisiert.
Screenshots und Serverlogs werden im temporären pytest-Verzeichnis abgelegt.

Eine zusätzliche Regression verwendet ein echtes iframe und eine synthetische
HA-Proxy-Antwort mit `Referrer-Policy: no-referrer`. Chromium erzeugt die
`Origin: null`-Header selbst; sie werden nicht im Test überschrieben. Sechs
POSTs prüfen Konto/Kategorie anlegen, archivieren und aktivieren. Der Testadapter
setzt den simulierten Supervisor-Peer ausschließlich im Browser-Testserver;
Produktivcode und echte TCP-Peer-Prüfung bleiben separat durch API-/Docker-
Tests abgesichert. Das ist keine Prüfung der HA-Anmeldung oder einer echten
Home-Assistant-Installation.

Neun weitere Abläufe erfassen Einnahmen/Ausgaben bei Mobil-/Desktopbreite,
hell/dunkel und Root/Präfix sowie im simulierten HA-Ingress mit Null-Origin.
Sie prüfen `100,00 → 87,66 → 87,67 €`, Zukunftsausschluss, ungültige Beträge,
Werterhalt samt Formular-ID, Notiz-Escaping und Persistenz nach Reload.

Alternativ kann ein vorhandenes Chromium verwendet werden (in dieser
Cloud-Umgebung tatsächlich mit Chromium **156.0.8078.79** geprüft):

```sh
LEBENSASSISTENT_CHROMIUM_EXECUTABLE=/usr/bin/chromium uv run --group browser --locked pytest tests browser_tests
```

### Lokale Präfixsimulation

Die Browsertests verwenden einen synthetischen Mount unter
`/synthetic-ingress/`. Zum manuellen Prüfen derselben Testkonfiguration:

```sh
umask 077
task_browser_data_dir=$(mktemp -d)
LEBENSASSISTENT_BROWSER_DATA_DIR="$task_browser_data_dir" uv run --locked uvicorn browser_tests.server:app --host 127.0.0.1 --port 8000
```

Dann **http://127.0.0.1:8000/synthetic-ingress/** öffnen. Navigation, Styles,
Icon und Zurück-Links behalten diesen Präfix bei. Alle URLs werden aus den
lokalen App-Routen und dem vertrauenswürdig konfigurierten ASGI-`root_path`
erzeugt. `X-Ingress-Path` und `X-Forwarded-Prefix` werden nicht ungeprüft
übernommen. Unbekannte Seiten liefern für Browser mit `Accept: text/html`
eine deutsche Fehlerseite mit echtem HTTP 404 bzw. 405; API-Clients behalten
JSON-Fehler. `/health` und Asset-Fehler bleiben unabhängig davon
JSON-Schnittstellen bzw. JSON-Fehlerantworten.

Diese Simulation verwendet den lokalen Entwicklungseinstieg und testet
Pfadverhalten, **keine HA-Authentifizierung oder echte Ingress-Integration**.
Der separate HA-Einstieg wird zusätzlich mit den nachfolgenden Container-
Tests geprüft. Den Entwicklungsserver ausschließlich an `127.0.0.1` starten.

### HA-Verpackung und Containerprüfungen (Etappe 0.3)

`config.yaml`, `repository.yaml` und `Dockerfile` liegen am Repository-Root.
Der Supervisor findet App-Konfigurationen rekursiv und nutzt deren Verzeichnis
als Build-Kontext; Quellcode wird weder dupliziert noch während des Builds aus
einem anderen Branch nachgeladen. Die Basisimages sind als Multiarch-Index
mit Digest festgehalten, Python- und uv-Version sind exakt festgelegt.

```sh
docker build --build-arg BUILD_ARCH=amd64 -t lebensassistent:alpha .
uv run --locked pytest container_tests
```

Die **6 Containerprüfungen** bauen ihr eigenes Image und erzeugen ausschließlich
UUID-benannte Testcontainer, ein privates Volume und ein internes Testnetz
mit Subnetz `172.30.32.0/24`. Der Entwicklungs-Dockerdaemon muss dieses Netz
frei haben. Es werden keine Hostports geöffnet. Ein Client mit TCP-Adresse
`172.30.32.2` simuliert den Supervisor; ein zweiter Client versucht Direktzugriffe
und Header-Fälschungen. Die Tests prüfen tatsächliche Prozessrechte, `/data`,
geordnete Stop-/Start-/Restart-Vorgänge und synthetische Persistenz bis zur
Container-Neuerstellung. Dabei werden zusätzlich DB-Integrität, WAL/FK und
Audit-/Migrationshistorie nach dem Neustart geprüft. Vor dem App-Start wird
synthetisch Schema 2 mit Konto, Kategorie und Test-Audit angelegt; der Start
migriert auf Schema 3 und erhält die Historie. Das ist ein Schema-Upgrade, kein behaupteter
Wechsel zwischen zwei alten/neuen Containerimages. Echte TCP-POSTs prüfen
Konten/Kategorien/Buchungen, CSRF-/Peer-Abweisung, Replay und Persistenz von
Buchungen und berechneten Salden über Restart/Neuerstellung.
Die SQLite-Datei unter
`/data` hat UID/GID 1000 und Modus 0600. Anschließend werden nur die eigenen Testressourcen
entfernt. Build- und Serverlogs liegen im temporären pytest-Verzeichnis.

Die Tests verschärfen den Betrieb zusätzlich mit schreibgeschütztem
Root-Dateisystem, `no-new-privileges` und nur CHOWN/FOWNER/SETUID/SETGID als
initialen Capabilities. Dies sind **Testbedingungen**, keine zugesicherten
Supervisor-Laufzeiteinstellungen. Der Server verwirft nach der Vorbereitung
seine Root-Rechte; die feste Startadresse im Container ist `0.0.0.0:8099`.
`proxy_headers=False` hält den echten TCP-Peer unverändert. Auch `/health`
benötigt den erlaubten Peer und ein gültiges Ingress-Präfix. Es gibt weder
einen Loopback-Bypass noch einen entsprechend ausgenommenen Watchdog.

Docker-Tests nutzen standardmäßig `unix:///var/run/docker.sock`. Ein anderer
Entwicklungsdaemon lässt sich über `LEBENSASSISTENT_DOCKER_HOST` wählen.
Für einen TLS-Proxy kann `LEBENSASSISTENT_BUILD_CA_FILE` auf ein lokales
CA-Bundle zeigen. Dann erzeugt der Test eine temporäre Dockerfile-Kopie mit
BuildKit-CA-Secret und `SSL_CERT_FILE`; die versionierte Dockerfile bleibt
unverändert, die CA wird nicht ins Image kopiert. TLS-Prüfung bleibt aktiv.

Vollständige lokale Regression mit Browser **und** Docker:

```sh
uv run --group browser --locked pytest tests browser_tests container_tests
```

Das sind **313 Tests**. In dieser Cloud-Umgebung werden zusätzlich
`LEBENSASSISTENT_CHROMIUM_EXECUTABLE=/usr/bin/chromium` und
`LEBENSASSISTENT_BUILD_CA_FILE=/etc/ssl/certs/ca-certificates.crt` gesetzt.
Paket-/Image-Downloads sind nur für Einrichtung und Build erforderlich.
Der Container-Test selbst läuft in einem internen Netz ohne externe Dienste.

Die Installation und erste Sichtprüfung von 0.0.1 auf HA wurden vom Nutzer
bestätigt; auch die erfolgreiche 403-Korrektur aus 0.0.4 wurde bestätigt.
Die neuen Buchungsfunktionen von 0.0.5, vollständige Sessionprüfung,
HA-Restart, AppArmor-Einbindung und der ARM-Nachweis sind weiterhin offen.
Für die HA-Prüfung ausschließlich die Repository-URL
mit **`#alpha`** aus [DOCS.md](../DOCS.md) verwenden. Der hier verfügbare
BuildKit-Worker unterstützt ausschließlich amd64; kein ARM- oder Zielgerätetest
wurde daraus abgeleitet.

Quellen: [Ingress-Anleitung](https://contributors.home-assistant.io/apps/guides/ingress/),
[Konfiguration](https://contributors.home-assistant.io/apps/reference/configuration/),
[Supervisor-Repositorysuche](https://github.com/home-assistant/supervisor/blob/main/supervisor/store/data.py).

### Aktuelle Projektstruktur

```text
.python-version                     # festgelegte lokale Python-Version
config.yaml                         # HA-App, Ingress, keine Hostports
repository.yaml                     # Metadaten des Alpha-App-Repositorys
Dockerfile / .dockerignore          # gesperrter, kleiner Container-Build
DOCS.md / CHANGELOG.md              # HA-Anleitung und Entwicklungsstand
pyproject.toml                      # Paket, Abhängigkeiten, pytest und Ruff
uv.lock                             # reproduzierbare Paketauflösung
src/lebensassistent/
    __init__.py
    main.py                         # App-Factory und ASGI-App
    api/
        __init__.py
        health.py                   # GET /health
        ui.py                       # HTML-Seiten, lokale URLs und Fehlerseiten
        views.py                    # gemeinsames Rendering/Formatierung
        catalog.py                  # Konten-/Kategorienformulare
        ledger.py                   # normale Einnahmen-/Ausgabenformulare
        forms.py                    # CSRF, Authority und begrenztes Form-Parsing
    frontend/
        templates/                  # Basis, Übersicht, Platzhalter, Fehlerseite
        static/                     # lokales CSS und SVG-Icon
    integrations/homeassistant/     # Ingress-Schutz und fester HA-Entrypoint
    database/                       # Connections, Migrationen, Audit und CLI
    services/                       # Konten/Kategorien, Buchungen, Salden und Werte
    repositories/                   # parametrisierter Katalog-Datenzugriff
tests/
    test_health.py                  # Health-Vertrag
    test_ui.py                      # synthetische API-/Präfix-Tests
    test_ingress.py                 # TCP-Peer- und Header-Vertrauenskette
    test_addon_runtime.py           # private Daten und Rechteabwurf
    test_addon_config.py            # minimale Rechte der HA-Konfiguration
    test_database.py                # WAL, FKs, Commit und Rollback
    test_migrations.py              # Fresh-DB, Upgrades und Versionshistorie
    test_audit.py                   # atomare, unveränderliche Audit-Einträge
    test_database_startup.py        # Startfehler, explizite Pfade und CLI
    test_catalog_values.py          # Geld-/Datumskonvertierung
    test_catalog_service.py         # Fachregeln, Audit und Upgrade
    test_catalog_http.py            # Formulare, CSRF und Eingabegrenzen
browser_tests/                      # separat ausführbare Playwright-Regression
container_tests/                    # echter Build und isolierter Lebenszyklus
docs/                               # verbindliche Vorgaben und Ergebnisse
```

Weitere Schichten aus `ARCHITEKTUR.md` werden erst in ihrer jeweiligen Etappe
angelegt. Etappe 1.3 beginnt ausschließlich nach ausdrücklicher Freigabe.

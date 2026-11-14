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
Eine HA-/Ingress-Konfiguration folgt erst in Etappe 0.3.

Die Oberfläche ist unter **http://127.0.0.1:8000/** erreichbar. Sie bietet eine
Übersicht und sieben weitere navigierbare Modulbereiche als Platzhalter.
Alle Texte, Styles und Icons werden lokal ausgeliefert; JavaScript und externe
Fonts/CDNs sind nicht erforderlich. Die Navigation funktioniert auch mit
Tastatur und ohne JavaScript. Ein Sprunglink führt direkt zum Hauptinhalt.
Das Theme folgt automatisch der Browser-/Systemeinstellung
`prefers-color-scheme`. Die Synchronisierung mit einer abweichenden manuellen
HA-Theme-Einstellung ist noch nicht implementiert oder getestet.

### Tests und Lint

```sh
uv run --locked pytest tests/test_health.py tests/test_ui.py
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv lock --check
```

Die ersten beiden Befehle prüfen die **25 Unit-/API-Tests ohne Browser**:

- `GET /health`: HTTP 200, JSON-Content-Type und exakte Antwort.
- `POST /health` mit synthetischem Inhalt: HTTP 405; Health bleibt unverändert.
- Ein erfundener, unbekannter Pfad: HTTP 404.
- Deutsche HTML-Seiten und alle acht Navigationsziele.
- Lokale Asset-Pfade und Browser-Fehlerseiten mit korrektem HTTP 404/405.
- Präfixerhalt bei ASGI-Mounts und gesetztem `root_path`, einschließlich
  mehrerer App-Mounts; Health behält auch für Browser-Anfragen sein JSON.
- Fehlende/private Assets bleiben unerreichbar; ungeprüfte Ingress-/Proxy-
  Header verändern keine Links.

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

Der erste Befehl führt **18 Browsertests** aus, der zweite die vollständige
Suite mit **43 API- und Browsertests**. Die Browserprüfungen starten selbst
einen lokalen Uvicorn-Prozess auf einem freien Loopback-Port und beenden ihn
anschließend. Sie prüfen 320/390/768/1280 Pixel, beide Themes, alle
Navigationsziele, Tastatur-Sprunglink, Seitenoverflow, Asset-/Konsolenfehler,
externe Anfragen sowie 404-Rücknavigation und einen Theme-Wechsel im Betrieb.
Screenshots und Serverlogs werden im temporären pytest-Verzeichnis abgelegt.

Alternativ kann ein vorhandenes Chromium verwendet werden (in dieser
Cloud-Umgebung tatsächlich mit Chromium **156.0.8078.79** geprüft):

```sh
LEBENSASSISTENT_CHROMIUM_EXECUTABLE=/usr/bin/chromium uv run --group browser --locked pytest tests browser_tests
```

### Lokale Präfixsimulation

Die Browsertests verwenden einen synthetischen Mount unter
`/synthetic-ingress/`. Zum manuellen Prüfen derselben Testkonfiguration:

```sh
uv run --locked uvicorn browser_tests.server:app --host 127.0.0.1 --port 8000
```

Dann **http://127.0.0.1:8000/synthetic-ingress/** öffnen. Navigation, Styles,
Icon und Zurück-Links behalten diesen Präfix bei. Alle URLs werden aus den
lokalen App-Routen und dem vertrauenswürdig konfigurierten ASGI-`root_path`
erzeugt. `X-Ingress-Path` und `X-Forwarded-Prefix` werden nicht ungeprüft
übernommen. Unbekannte Seiten liefern für Browser mit `Accept: text/html`
eine deutsche Fehlerseite mit echtem HTTP 404 bzw. 405; API-Clients behalten
JSON-Fehler. `/health` und Asset-Fehler bleiben unabhängig davon
JSON-Schnittstellen bzw. JSON-Fehlerantworten.

Diese Simulation testet Pfadverhalten, **keine HA-Authentifizierung oder echte
Ingress-Integration**. HA-Verpackung und Zugriffsschutz folgen in Etappe 0.3;
bis dahin ausschließlich an `127.0.0.1` starten.

### Aktuelle Projektstruktur

```text
.python-version                     # festgelegte lokale Python-Version
pyproject.toml                      # Paket, Abhängigkeiten, pytest und Ruff
uv.lock                             # reproduzierbare Paketauflösung
src/lebensassistent/
    __init__.py
    main.py                         # App-Factory und ASGI-App
    api/
        __init__.py
        health.py                   # GET /health
        ui.py                       # HTML-Seiten, lokale URLs und Fehlerseiten
    frontend/
        templates/                  # Basis, Übersicht, Platzhalter, Fehlerseite
        static/                     # lokales CSS und SVG-Icon
tests/
    test_health.py                  # Health-Vertrag
    test_ui.py                      # synthetische API-/Präfix-Tests
browser_tests/                      # separat ausführbare Playwright-Regression
docs/                               # verbindliche Vorgaben und Ergebnisse
```

Weitere Schichten aus `ARCHITEKTUR.md` werden erst in ihrer jeweiligen Etappe
angelegt. Etappe 0.3 beginnt ausschließlich nach ausdrücklicher Freigabe.

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

## Lokale Entwicklung (Etappe 0.1)

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

### Tests und Lint

```sh
uv run --locked pytest tests/test_health.py
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv lock --check
```

Der erste Befehl prüft gezielt die neue API, der zweite führt sämtliche
vorhandenen Tests als Regression aus. Aktuell sind das dieselben drei Tests:

- `GET /health`: HTTP 200, JSON-Content-Type und exakte Antwort.
- `POST /health` mit synthetischem Inhalt: HTTP 405; Health bleibt unverändert.
- Ein erfundener, unbekannter Pfad: HTTP 404.

Jeder Test verwendet eine eigene App-Instanz mit FastAPI-Testclient. Es werden
keine persönlichen Daten, Laufzeitdatenbanken oder laufenden HA-Systeme
benötigt. Warnungen sind in pytest als Fehler konfiguriert. Ein tatsächlicher
Serverstart mit curl ergänzt die API-Tests. Erfolgreiche lokale Prüfungen sind
keine Abnahme auf Home Assistant OS oder ARM/Raspberry Pi.

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
tests/
    test_health.py                  # synthetische API-Tests
docs/                               # verbindliche Vorgaben und Ergebnisse
```

Weitere Schichten aus `ARCHITEKTUR.md` werden erst in ihrer jeweiligen Etappe
angelegt. Etappe 0.2 beginnt ausschließlich nach ausdrücklicher Freigabe.

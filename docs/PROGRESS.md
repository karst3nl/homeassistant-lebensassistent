# Entwicklungsfortschritt

## Stand
- Status: **Etappe 0.1 lokal implementiert und geprüft**; Freigabepause.
- Aktiver Branch: `alpha`; `main` nur Platzhalter, nicht bearbeiten.
- Abgeschlossene Etappe: **0.1** — Projektstruktur, lokaler FastAPI-Server, Health-Endpunkt, pytest und Ruff.
- Geprüft: API-Tests, vollständige lokale Regression, Lint/Format, Lockfile, frische virtuelle Umgebung, tatsächlicher HTTP-Serverstart und geordnetes Herunterfahren.
- Noch nicht geprüft: Home-Assistant-Integration, Ingress, ARM-/Raspberry-Pi-Betrieb. Datenbankmigrationen sind mangels Datenbank noch nicht anwendbar.
- Nächster Schritt: **Explizite Nutzerfreigabe für Etappe 0.2 abwarten**; noch keine Arbeiten daran begonnen.

## Etappenlog
| Etappe | Status | Tests | Freigabe |
|---|---|---|---|
| 0.1 Grundgerüst und Health | Lokal abgeschlossen | 3 API-Tests grün; Regression, Lint/Format, Setup und HTTP-Start grün | Ergebnis zur Abnahme vorgelegt |
| 0.2 Responsive UI | Offen | — | Ausstehend |
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

### Datenschutz und offene Prüfungen

Vorgemerkten Diff manuell geprüft und automatisierten Secret-Scan ausgeführt.
Die Tests enthalten ausschließlich synthetische HTTP-Anfragen. Es wurden
keine privaten Daten, Zugangsdaten, Datenbanken oder Backups hinzugefügt.
Der Scan lief ohne externe Verifikation möglicher Geheimnisse.

Der Health-Endpunkt ist ein Lebenszeichen des lokalen Webservers und keine
Integrations- oder Datenbankprüfung. **Home Assistant OS, Ingress und
ARM/Raspberry Pi wurden nicht getestet.** Die HA-Verpackung ist erst für
Etappe 0.3 vorgesehen. Für Etappe 0.2 liegt noch keine Nutzerfreigabe vor.

### Abschlusscheckliste

- [x] Etappe 0.1 implementiert.
- [x] Tests und Start lokal tatsächlich ausgeführt; Lint und Regression grün.
- [ ] HA-Laufzeittest (ausstehend).
- [ ] Nutzerfreigabe für Etappe 0.2.

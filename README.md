# Home Assistant Lebensassistent

Personal finance, vehicle and project management for Home Assistant.

Development takes place exclusively on the [`alpha`](../../tree/alpha) branch until the application is ready for its first release.

No personal financial information, real account data, credentials, or production backups belong in this repository.

## Lokaler Entwicklungsstand

Etappen 0.1 und 0.2 stellen einen lokalen FastAPI-Webserver mit responsiver
deutscher Basisoberfläche, Navigation und automatischem Hell-/Dunkel-Theme
bereit. `GET /health` liefert HTTP 200 und `{"status":"ok"}`.
Die Modulbereiche sind als „In Vorbereitung“ gekennzeichnet. Etappe 0.3 ergänzt
eine experimentelle HA-App-Verpackung mit Ingress-Schutz und privatem `/data`.
Finanzverwaltung und Datenbank folgen in späteren Etappen. Docker wurde lokal
auf amd64 geprüft; echte HA-OS-/Ingress- und ARM-Prüfungen stehen noch aus.

Die [HA-App-Anleitung](DOCS.md) verwendet ausschließlich das Repository mit
**`#alpha`**. Es werden keine Hostports veröffentlicht.

Einrichtung, Projektstruktur sowie Start- und Testbefehle stehen in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#lokale-entwicklung).
Durchgeführte Prüfungen und offene Integrationsprüfungen stehen in
[docs/PROGRESS.md](docs/PROGRESS.md).

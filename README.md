# Home Assistant Lebensassistent

Personal finance, vehicle and project management for Home Assistant.

Development takes place exclusively on the [`alpha`](../../tree/alpha) branch until the application is ready for its first release.

No personal financial information, real account data, credentials, or production backups belong in this repository.

## Lokaler Entwicklungsstand

Etappe 0.1 stellt einen minimalen FastAPI-Webserver mit `GET /health` bereit.
Der Endpunkt liefert HTTP 200 und `{"status":"ok"}`. Es gibt noch keine
Finanzverwaltung, Datenbank, Benutzeroberfläche oder Home-Assistant-Verpackung.

Einrichtung, Projektstruktur sowie Start- und Testbefehle stehen in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#lokale-entwicklung-etappe-01).
Durchgeführte Prüfungen und offene Integrationsprüfungen stehen in
[docs/PROGRESS.md](docs/PROGRESS.md).

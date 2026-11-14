# Änderungen

## 0.0.2 — SQLite-Grundlage

- Private Datenbank unter `/data/lebensassistent.sqlite3`, beim Start angelegt
  und vor Annahme von Anfragen migriert.
- WAL, Fremdschlüssel und explizite atomare Transaktionen.
- Versionierte Migrationen mit Prüfsummen und Audit-Protokoll; fehlerhafte
  oder nicht unterstützte Datenbanken verhindern den Start.
- Automatisierte Fresh-DB-, Upgrade-, Rollback- und Persistenzprüfungen.
- Noch keine Konten-, Buchungs- oder weiteren Fachfunktionen.

Die Installation und erste Sichtprüfung von 0.0.1 wurden vom Nutzer auf seinem
Home Assistant bestätigt. Das Update auf 0.0.2 muss dort noch geprüft werden.

## 0.0.1 — experimenteller Entwicklungsstand

- Lokaler FastAPI-Health-Endpunkt und responsive deutsche Basisoberfläche.
- Navigation und automatisches Browser-/System-Theme.
- Erste HA-App-Verpackung für den Entwicklungsbranch `alpha`, mit internem
  Ingress-Port und ohne veröffentlichte Hostports.
- Zugriffsschutz anhand des echten Supervisor-Peers, validierte Präfixe und
  originrelative Redirects.
- Private `/data`-Vorbereitung und anschließender Rechteabwurf auf UID/GID 1000.
- Automatisierte API-, Browser- und lokale Docker-Lebenszyklustests.

HA OS, echte Ingress-Sessionprüfung und ARM-Laufzeit sind noch nicht abgenommen.

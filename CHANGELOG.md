# Änderungen

## 0.0.3 — Konten und Kategorien

- Erste bedienbare Masken im Bereich „Konten & Buchungen“.
- Konten mit Name, Kontoart, centgenauem Anfangssaldo, Startdatum und optionaler
  Notiz anlegen. Negative Anfangssalden sind erlaubt.
- Konten archivieren und wieder aktivieren; Anfangssaldo und Startdatum bleiben
  nach der Anlage unverändert.
- Kategorien für Einnahmen/Ausgaben und optionale Unterkategorien anlegen,
  archivieren und aktivieren.
- Migration auf Schema 2 erhält die bestehende Audit-Historie; Änderungen
  werden atomar mit ihrem Audit-Protokoll gespeichert.
- CSRF-Schutz, begrenzte Formulare, HTML-Escaping und nicht cachebare Finanzseiten.
- Noch keine Buchungen, Transfers, Budgets oder Saldenberechnung aus Bewegungen.

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

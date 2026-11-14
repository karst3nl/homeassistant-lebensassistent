# Änderungen

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

# Architektur und Qualität

## Ziel
Lokal betreibbare Home Assistant App (vormals Add-on) mit Ingress, eigener Python/FastAPI-API, schlankem HTML/CSS/JS-Frontend und SQLite im persistenten App-Speicher. Die Anwendung ist fachlich ohne Home Assistant isoliert testbar; HA wird durch einen Adapter für Benachrichtigungen und Ingress eingebunden.

## Schichten
- `api/`: Requestvalidierung, Zugriffsschutz, DTOs, schlanke Endpunkte
- `services/`: Geschäftslogik für Ledger, Fixkosten, Liquidität, Sparen, Fahrzeuge, Projekte, Timer, Notifications
- `repositories/`: Datenzugriff, Transaktionen, atomare Updates
- `database/`: SQLite-Migrationen, Constraints, Integritätschecks
- `frontend/`: responsive UI, keine Finanzberechnungen als alleinige Client-Wahrheit
- `integrations/homeassistant/`: Benachrichtigungen, App-Umgebung, Ingress
- `tests/`: synthetische Unit-/Integrationstests

Diese Schichten beschreiben die **Zielstruktur**. Der tatsächlich implementierte Umfang steht in [PROGRESS.md](PROGRESS.md). Dateistruktur nur etappenweise erstellen.

## SQLite-Grundlage (Etappe 0.4)

`database/` enthält eine Connection-Factory, explizite Transaktionsgrenzen,
eine unveränderliche Migrationsregistry und den Audit-Schreibhelfer. Zunächst
existieren nur `schema_migrations` und `audit_log`. Fachliche Tabellen folgen
in ihren jeweiligen Etappen.

Jede Verbindung aktiviert WAL, Fremdschlüssel, vollständige Synchronisierung
und einen begrenzten Lock-Timeout. Migrationen beginnen vor dem Lesen der
Historie mit `BEGIN IMMEDIATE`; Schema, Versionsmarke und Audit sind atomar.
Ein Audit-Eintrag verwendet dieselbe bereits aktive Transaktion wie die
Änderung. Es gibt keine global geteilten SQLite-Verbindungen.

Der HA-Entrypoint übergibt fest `/data/lebensassistent.sqlite3`. Die Migration
läuft im App-Lifespan vor dem ersten HTTP-Zugriff und nach dem Rechteabwurf.
Die lokale Entwicklung verwendet nur bei expliziter Pfadangabe eine Datenbank;
Imports und die Standard-Test-App erzeugen keine Repository-Datenbank.

## Datenschutz / Betrieb
- Alle privaten Laufzeitdaten bleiben unter HA-App-`/data` und werden niemals committet.
- Kein direkter ungeschützter Netzwerkport, kein öffentliches API, keine Cloudpflicht.
- Externe Home-Assistant-Schnittstelle klein halten und separat absichern.
- Konfiguration/Secrets nicht als Quellcode hinterlegen.
- Centgenaue Ledger-Beträge, transaktionale Writes, auditierbare Korrekturen und FK-Constraints.

## Einführungs-/Teststrategie
Testbare FastAPI-Minimalkomponente → SQLite/Migrationsschema → Finanzkern → weitere Module → HA-Integrationsprüfung auf Zielhardware. Softwaretests lokal zuerst; HA- und Raspberry-Pi-Tests ausdrücklich offen halten, bis sie wirklich ausgeführt wurden.

Siehe [Pflichtenheft](PFLICHTENHEFT.md), [Etappenplan](IMPLEMENTATION_PLAN.md), [Codex-Regeln](../AGENTS.md).

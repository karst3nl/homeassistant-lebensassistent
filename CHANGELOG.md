# Änderungen

## 0.0.6 — Buchungen auf Kategorien aufteilen

- Einnahmen und Ausgaben auf zwei bis zwanzig positive Teilbeträge mit
  Kategorie und optionaler Teilnotiz aufteilen. Die Summe muss exakt passen.
- Zeilen ohne JavaScript hinzufügen/entfernen; Eingaben bei Fehlern erhalten.
- Alle Teile, Gesamtbuchung und Audit gemeinsam atomar speichern.
- Wiederholte oder konkurrierende Formularübermittlung bleibt vor Doppelanlage
  geschützt; geänderte Teilbeträge/Notizen mit derselben Formular-ID ergeben Konflikt.
- Buchungsliste zeigt alle Teile; Kontosalden zählen die Gesamtbuchung einmal.
- Einzelbuchungen und Datenbankschema 3 bleiben kompatibel. Keine Migration,
  Umbuchungen, Rückerstattungen oder nachträglichen Buchungskorrekturen.

## 0.0.5 — Einnahmen, Ausgaben und Kontosalden

- Einnahmen und Ausgaben mit Konto, passender Kategorie, positivem Eurobetrag,
  Datum (Standard heute in Europe/Berlin) und optionaler Notiz erfassen.
- Buchung, vollständige Kategoriezuordnung und Audit gemeinsam atomar speichern;
  wiederholte Übermittlung desselben Formulars erzeugt keine Doppelbuchung.
- Kontosalden aus Anfangssaldo und gebuchten Bewegungen berechnen. Zukünftig
  datierte Einträge werden gekennzeichnet und zählen erst ab ihrem Datum.
- Letzte 50 Buchungen anzeigen; archivierte Konten/Kategorien behalten ihre Historie.
- Schema 3 erhält Konten, Kategorien und Audit aus älteren Versionen.
- Noch keine Mehrfachaufteilungen, Umbuchungen, Rückerstattungen oder Stornierungen.

## 0.0.4 — Formular-403 unter Home-Assistant-Ingress

- Fehler bei der Konten-/Kategorienanlage und Statusänderung behoben:
  Home Assistants `Referrer-Policy: no-referrer` führt bei normalen
  Browser-Formularen zu `Origin: null`.
- Diesen Wert nur hinter verifiziertem Ingress und mit gültigem CSRF-Token
  akzeptieren. Direkte Zugriffe, fremde Fetch-Site und fehlende/falsche Tokens
  bleiben gesperrt.
- Browserregression mit tatsächlich vom Browser erzeugtem `Origin: null`
  sowie API-/Container-Negativtests ergänzt.
- Keine neue Fachfunktion oder Schemaänderung; Schema 2 bleibt erhalten.

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

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
eine unveränderliche Migrationsregistry und den Audit-Schreibhelfer. Migration 1
legt `schema_migrations` und `audit_log` an; Migration 2 ergänzt in Etappe 1.1
`accounts` und `categories`. Migration 3 ergänzt `transactions` und
`transaction_splits` für Normalbuchungen. Weitere Tabellen folgen in ihren Etappen.

Jede Verbindung aktiviert WAL, Fremdschlüssel, vollständige Synchronisierung
und einen begrenzten Lock-Timeout. Migrationen beginnen vor dem Lesen der
Historie mit `BEGIN IMMEDIATE`; Schema, Versionsmarke und Audit sind atomar.
Ein Audit-Eintrag verwendet dieselbe bereits aktive Transaktion wie die
Änderung. Es gibt keine global geteilten SQLite-Verbindungen.

Der HA-Entrypoint übergibt fest `/data/lebensassistent.sqlite3`. Die Migration
läuft im App-Lifespan vor dem ersten HTTP-Zugriff und nach dem Rechteabwurf.
Die lokale Entwicklung verwendet nur bei expliziter Pfadangabe eine Datenbank;
Imports und die Standard-Test-App erzeugen keine Repository-Datenbank.

## Konten und Kategorien (Etappe 1.1)

`services/catalog.py` validiert die Fachoperationen und hält Änderung und Audit
in derselben Transaktion. `repositories/catalog.py` kapselt das parametrisierte
SQL. Anfangssaldo und Startdatum sind nur bei Anlage setzbar; Statuswechsel
ändern diese Werte nicht. Archivierung ist reversibel und löscht keine Historie.

Kategorien können bei Anlage eine aktive Oberkategorie derselben Art erhalten.
Ein zusammengesetzter FK sichert die Art; aktive Kinder verhindern eine
Elternarchivierung. Es gibt keine Umhängung und dadurch keine neuen Zyklen.

Die HTTP-Schicht rendert HTML-Formulare ohne JavaScript. Ein zufälliger Token pro
App-Instanz ist für jeden schreibenden Aufruf erforderlich; Vergleich konstantzeitlich.
Fetch-Site und Origin-Authority werden ergänzend geprüft. X-Forwarded-Host wird
nur nach bestätigter Ingress-Prüfung als zusätzliche Authority berücksichtigt;
X-Forwarded-Proto verändert weder ASGI-Scheme noch Authentifizierung. Der
Authority-Abgleich ist keine vollständige Scheme-/Origin-Prüfung und ersetzt
den Token nicht. Finanzseiten sind nicht cachebar; Jinja maskiert Benutzereingaben.

Home Assistant setzt auf Antworten `Referrer-Policy: no-referrer`; native
Browser-POSTs können dadurch `Origin: null` senden. Genau dieser einzelne Wert
wird seit 0.0.4 nur hinter verifiziertem Ingress und nach erfolgreicher
Tokenprüfung akzeptiert. Fetch-Site wird weiterhin vorher geprüft. Lokal,
bei doppeltem Origin, fremdem Peer oder fehlendem/falschem Token bleibt der
Zugriff gesperrt. Die Antwortpolicy wird nicht abgeschwächt.

`services/values.py` verarbeitet Eurotext ausschließlich mit Integerarithmetik.
Gespeicherte Einzelbeträge bleiben als Integer-Cent im signierten
SQLite-64-Bit-Bereich; negative Anfangssalden
sind zulässig. Konto-/Kategorieeingaben verwenden strikt validierte DTOs.
## Einnahmen, Ausgaben und Salden (Etappe 1.2)

`services/ledger.py` prüft aktive Konten und passende aktive Kategorien sowie
ein Buchungsdatum ab Kontostart. `repositories/ledger.py` speichert Buchung und
bei Normalbuchungen eine vollständige Kategoriezuordnung; deren gemeinsamer
Audit-Snapshot liegt in derselben `BEGIN IMMEDIATE`-Transaktion.

Positive Einzelbeträge bleiben Integer-Cent im SQLite-int64-Bereich. Die Richtung
ergibt sich aus Einnahme/Ausgabe. Salden werden aus `transactions` berechnet,
ohne Split-JOIN oder gespeichertes Saldofeld. Ein SQL-Snapshot liefert die
Bewegungen; Python-Integer vermeiden Overflow bei großen aggregierten Summen.
Nur `posted` bis zum Stichtag zählt. Vor Kontoöffnung ist der Saldo unbekannt;
archivierte Konten behalten ihre Historie. Zukünftige Daten sind zulässig,
sichtbar markiert und bis dahin aus dem heutigen Saldo ausgeschlossen.

Eine technische eindeutige `submission_id` verhindert doppelte Übermittlung
derselben Formularanfrage. Identischer Inhalt liefert die vorhandene Buchung;
abweichender Inhalt führt zum Konflikt. Die Prüfung erfolgt innerhalb derselben
Schreibtransaktion vor erneuten Aktivitätsprüfungen. Ein frisches Formular
erlaubt eine neue, bewusst auch inhaltlich gleiche Buchung. Die ID ersetzt
weder CSRF-Token noch Ingress-Authentifizierung.

`api/ledger.py` verarbeitet das servergerenderte Buchungsformular über dieselben
begrenzten Form-/CSRF-Prüfungen. Datum ist standardmäßig heute in Europe/Berlin.
Die Finanzansicht zeigt aktuelle Salden, Anfangssalden und die letzten 50
Buchungen. Keine Änderungs-, Storno- oder Transfer-Routen.

## Kategorieaufteilungen (Etappe 1.3)

`SplitPostingInput` validiert zwei bis zwanzig positive `SplitInput`-Teilbeträge
mit Kategorie und optionaler Teilnotiz. Die Python-Integer-Summe muss exakt
dem Gesamtbetrag entsprechen. `LedgerService.post_split` und die bestehende
Normalbuchung verwenden denselben normalisierten, atomaren Speicherpfad.
Alle Kategorien werden in der Schreibtransaktion auf Aktivität und passende
Art geprüft. Bei einem Fehler eines späteren Teils rollt auch der Elternsatz
zurück. Der Audit-Snapshot enthält alle Teile in ihrer Reihenfolge.

Replay vergleicht Kernfelder und die vollständige geordnete Liste aus Kategorie,
Betrag und Teilnotiz. Änderungen an irgendeinem Teil führen zum Konflikt;
parallele Wiederholungen erzeugen keine Doppelanlage. Der Betrag im Elternsatz
bleibt die einzige Quelle für Kontosalden. Die Listenabfrage begrenzt in einer
CTE zunächst die Elternbuchungen, hängt anschließend alle Teile an und liefert
einen konsistenten SQL-Snapshot. Das Limit schneidet keine Teilbeträge ab.

`api/splits.py` bietet das eigenständige HTML-Formular. Add/Remove-Aktionen
durchlaufen CSRF/Ingress-/Origin-Prüfungen und ändern nur die dargestellten
Zeilen. Das Standard-Feldlimit bleibt 16; ausschließlich diese Route verwendet
70 Felder bei unverändertem 32-KiB-Bodylimit. Zeilenzahl, Index und überzählige
Felder werden geprüft; leere Zeilen werden beim Speichern nicht ignoriert.
Schema 3 und alle bisherigen Migrationen bleiben unverändert. Fahrzeug- und
Projektzuordnungen folgen erst mit den jeweiligen Modulen.

## Datenschutz / Betrieb
- Alle privaten Laufzeitdaten bleiben unter HA-App-`/data` und werden niemals committet.
- Kein direkter ungeschützter Netzwerkport, kein öffentliches API, keine Cloudpflicht.
- Externe Home-Assistant-Schnittstelle klein halten und separat absichern.
- Konfiguration/Secrets nicht als Quellcode hinterlegen.
- Centgenaue Ledger-Beträge, transaktionale Writes, auditierbare Korrekturen und FK-Constraints.

## Einführungs-/Teststrategie
Testbare FastAPI-Minimalkomponente → SQLite/Migrationsschema → Finanzkern → weitere Module → HA-Integrationsprüfung auf Zielhardware. Softwaretests lokal zuerst; HA- und Raspberry-Pi-Tests ausdrücklich offen halten, bis sie wirklich ausgeführt wurden.

Siehe [Pflichtenheft](PFLICHTENHEFT.md), [Etappenplan](IMPLEMENTATION_PLAN.md), [Codex-Regeln](../AGENTS.md).

# Implementierungsplan — ausschließlich Branch `alpha`

Status: Etappen 0.1 bis 0.4 und 1.1 lokal umgesetzt; App-Version 0.0.4 mit Korrektur des gemeldeten Formular-403 unter Ingress. Installation/Sichtprüfung von 0.0.1 auf HA vom Nutzer bestätigt; Korrektur-/Security-/ARM-Abnahme auf HA weiter offen. Etappe 1.2 wartet auf Nutzerfreigabe. Prüfergebnisse: [PROGRESS.md](PROGRESS.md). Quelle: [Pflichtenheft](PFLICHTENHEFT.md) und [AGENTS.md](../AGENTS.md).

## Verbindlicher Entwicklungsmodus
Eine Etappe besteht aus: Anforderung lesen → Mini-Design/Tests definieren → klein implementieren → Unit/API-Tests → Regression → Datenschutz-Review → Dokumentation/Commit auf `alpha` → **anhalten und Freigabe abwarten**. Keine parallele Großimplementierung. `main` nie verändern.

Alle Testdaten sind synthetisch. Immer zuerst lokal ohne laufenden Home Assistant testbar bauen. Sobald die HA-App lauffähig ist, zusätzliche Integrationsprüfungen. Nicht verfügbare Hardwaretests als offen deklarieren.

## Etappe 0 — Fundament
- **0.1:** Projektverzeichnisse, minimaler FastAPI-Server mit /health, reproduzierbarer lokaler Start, pytest-Test, Dokumentation, keine Datenbank- oder Finanzfunktion. Gate: Health-Test, Teststart und Lint grün.
- **0.2:** Statische responsive UI, Basisnavigation, Theme, Ingress-Pfadkompatibilität; Test für Asset-Pfade, Fehlerseiten und Mobil-Layout. Gate: UI lokal bedienbar, keine externe Abhängigkeit.
- **0.3:** Home-Assistant-App-Verpackung mit Dockerfile/Config, Persistent-Data-Pfad, minimale Berechtigungen, Ingress; Start-/Stop-/Restart-Test auf HA OS, sofern verfügbar. Gate: keine öffentliche ungeschützte API.
- **0.4:** SQLite-Connection, Migrationstool, FK und Transaktionsgrenzen, isolierte Testdatenbank, grundlegendes Audit. Gate: Fresh-DB und Upgrade-Migration reproduzierbar, Neustart mit persistenten Daten.

## Etappe 1 — Buchungskern
- **1.1:** Echte Konten (Anfangssaldo/-datum, archivieren), Kategorien; negative/ungültige Eingaben testen.
- **1.2:** Einnahmen und Ausgaben, atomare Buchung, Cent-Präzision, berechnete Salden; Abfrage- und Saldo-Tests.
- **1.3:** Transaktionssplits, Summe muss exakt aufgehen; Validierungs-/Race-Tests.
- **1.4:** Umbuchungen als atomisches Buchungspaar, kein Einkommen/Verbrauch; Tests für Fehler mitten im Transfer.
- **1.5:** Verknüpfte volle/teilweise Rückerstattungen, anteiliger Vorschlag mit manueller Korrektur; keine Übererstattung ohne Warnung.
- **1.6:** Kontostandsabgleich nur lesend, historische Korrekturen/Audit, einfache Eingabemasken. Gate: alle Ledger-Invarianten und Regression grün.

## Etappe 2 — Finanzplanung und Fixkosten
- **2.1:** Wiederholungsregeln und konkrete Fälligkeiten einschließlich eindeutiger Zahlungserkennung/Teilzahlung, Plan!=Ist.
- **2.2:** Standardgehalt, Sonderzahlungen, kalender-/gehaltsmonatliche Periode (ohne Überlappung).
- **2.3:** Rest-Monatsbudget, Plan/Ist/Abweichung. Test: keine doppelte Erfassung fälliger und gebuchter Ausgaben.
- **2.4:** Sofortige Liquidität mit einstellbarem Horizont (Default bis zum nächsten Gehalt), frei/bereits gebunden; keine ungebuchten Einnahmen zählen.
- **2.5:** Rollierende 12-Monats-Prognose für Fixkostenkonto, minimale Cent-Überweisungsempfehlung, sofortige Deckungslücken; Monats-/Jahresgrenzen und Fälligkeit vor erstem Einzahlungstermin testen.
Gate: nachvollziehbare Beispielrechnungen und Grenzfalltests.

## Etappe 3 — Sparziele
- **3.1:** Ziele und tatsächliche Kontozuordnungen; kein virtuelles Bankguthaben.
- **3.2:** Mehrere Ziele je Konto, keine doppelte Zuordnung im gedeckten Zustand.
- **3.3:** Abhebung trotz Unterdeckung erlaubt; Review-Status und manuelle Neuverteilung.
Gate: unveränderte Kontosalden durch reine Zuordnung, Konflikte klar sichtbar.

## Etappe 4 — Fahrzeuge
- **4.1:** Fahrzeugprofile, beliebig viele, archivieren.
- **4.2:** Tankvorgang: nur Fahrzeug/Betrag/Konto Pflicht, wahlweise Literpreis oder Gesamtbetrag; finanzielle Einmalbuchung.
- **4.3:** Verbrauch nur bei hinreichenden Kilometer-/Volltankdaten, Umgang mit Teilbetankung.
- **4.4:** Service-/Reparaturpositionen, Eigenarbeitszeit, Kosten ausschließlich aus verknüpften Buchungssplits.
- **4.5:** Kosten pro km und Fahrzeugtermine; Test auf fehlende Daten und doppelte Kosten.

## Etappe 5 — Projekte, Kalender, Zeit
- **5.1:** Projekte/Aufgaben mit Priorität und Status, Fortschritt nur erledigte / aktive Aufgaben.
- **5.2:** Materialliste, Einkäufe/Zuordnung, nur reale verknüpfte Buchungen als Kosten, keine Projektbudgets.
- **5.3:** Serverseitiger Timer, genau einer aktiv; manueller Zeiteintrag, Überlappungsprüfung.
- **5.4:** Neustart/Unterbrechung → review_required; erst nach Prüfung bestätigte Stunden.
- **5.5:** Tages- und Wochenkalender, Terminverschiebung, Mobilansicht.

## Etappe 6 — Dashboard und Meldungen
- **6.1:** Dashboard mit Monatsbudget an erster Stelle, sofort verfügbar separat, Widgets dauerhaft ein-/ausblenden und sortieren.
- **6.2:** Sechs Schnellaktionen, End-to-End-Integration.
- **6.3:** Individuelle Erinnerungsvorwarnungen, persistente Queue, nach Neustart relevante Meldungen nachholen, Deduplizierung.
- **6.4:** Wöchentliche Zusammenfassung am konfigurierten Wochentag/Uhrzeit, HA-Notifications, Theme-System.

## Etappe 7 — Abschluss und Releaseprüfung
- **7.1:** CSV-Exporte, druckfreundliche HTML-Berichte; kein CSV-Import/PDF-Generator.
- **7.2:** SQLite-konsistenter manueller Backup-/Restore-Prozess, sichere Integritätsprüfung.
- **7.3:** HA-Backup, Ingress-Schutz, UI-Responsiveness, ARM-Hardware-/Neustarttest.
- **7.4:** End-to-End-Finanz-/Fahrzeug-/Projekt-Regression, Datenschutz-/Secret-Review, Fehlerfalltests.
- **7.5:** Veröffentlichung einer Release-Checkliste; **nicht nach `main` mergen**. Nur der Nutzer entscheidet über die Freigabe.

## Abnahme jeder einzelnen Etappe
1. Neue Tests grün; bestehende Tests grün.
2. Negative Eingaben, Grenzen, Migration und Neustart wo relevant geprüft.
3. Keine persönlichen Testdaten, Secrets oder Datenbanken in Git.
4. Code/Anforderungen und `docs/PROGRESS.md` stimmen überein.
5. Commit ausschließlich auf `alpha`, Hash protokolliert.
6. Bekannte Risiken und fehlende HA-Hardwareprüfungen offengelegt.
7. Auf explizite Freigabe zur nächsten Etappe warten.

## Codex-Startauftrag
Lies `AGENTS.md`, `docs/DEVELOPMENT.md`, `docs/PFLICHTENHEFT.md` und diesen Plan. Prüfe `git branch --show-current` ist `alpha`. Setze **ausschließlich Etappe 0.1** um. Erstelle Tests, führe sie aus, aktualisiere `docs/PROGRESS.md`, committe nur auf `alpha` und stoppe. Bericht mit Testbefehlen/-ergebnissen und offenen Punkten.

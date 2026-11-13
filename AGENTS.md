# AGENTS.md — Codex-Arbeitsregeln

## Auftrag
Entwickle **Lebensassistent**, eine lokal betriebene Home-Assistant-App für Finanzen, Konten, Fixkosten, Sparziele, Fahrzeuge, Projekte, Zeiterfassung und Erinnerungen. Die Dokumentation unter `docs/` ist die Produktquelle. Lies vor jeder Arbeit zuerst `docs/PFLICHTENHEFT.md`, `docs/IMPLEMENTATION_PLAN.md` und `docs/DEVELOPMENT.md`.

## Verbindlicher Branch-Workflow
- **Ausschließlich auf `alpha` entwickeln, committen und pushen.** Prüfe den Branch zu Beginn jeder Session (`git status -sb`, `git branch --show-current`).
- Wenn `alpha` nicht aktiv ist, wechsle dorthin. Falls das nicht sicher möglich ist: stoppen und berichten.
- **Nie in `main` committen oder pushen, nie selbstständig mergen, nie automatisch einen PR abschließen.**
- `main` bleibt unberührt, bis der Eigentümer die vollständig geprüfte App ausdrücklich freigibt.
- Keine Force-Pushes, kein Rebase/Reset auf fremde Commits ohne ausdrückliche Freigabe.

## Datenschutz und sichere Beispieldaten
- Dieses GitHub-Repository ist öffentlich. **Keine persönlichen Daten** in Dateien, Commits, Issues, Pull Requests, Screenshots oder Logs.
- Nur synthetische Testdaten: erfundene Namen, erfundene Fahrzeuge/Kennzeichen, generische Konten und Beträge.
- Niemals echte Finanzbuchungen, Bankdaten, Kontostände, persönliche Einkommen, API-Tokens, Adressen, lokale HA-URLs, Geheimnisse, Backups oder Laufzeit-DB committen.
- `.gitignore` ist kein Ersatz für `git diff --cached` und Secret-Scanning vor dem Commit.
- Kein Upload echter Daten an externe APIs oder LLM-Dienste. Keine unnötige Telemetrie.
- Bei Verdacht auf Datenabfluss: **nicht pushen**, Fundort nennen, erst bereinigen.

## Arbeitsweise: kleine, abgeschlossene Schritte
1. Lies die relevante Anforderung und den aktuellen Etappenstatus.
2. Beschreibe vor der Änderung kurz Ziel, betroffene Dateien, fachliche Invarianten und Tests.
3. Implementiere **nur den nächsten kleinsten überprüfbaren Schritt** der aktuellen Etappe. Keine unaufgeforderten Features.
4. Schreibe/aktualisiere zuerst geeignete Tests, insbesondere für Geldbewegungen und Migrationen.
5. Führe die kleinsten passenden Tests aus; danach alle bisher ausführbaren Regressionstests.
6. Behebe Fehler in derselben Etappe. Bei unlösbarer Blockade stoppen, nicht zur nächsten Etappe springen.
7. Ergänze bei Bedarf Dokumentation und `docs/PROGRESS.md`: erledigt, Tests, Risiken, nächster Schritt.
8. Committe nur nach grünen Tests und Review der Änderungen auf `alpha`; kleine, verständliche Commits.
9. Berichte: Dateien, Funktionsverhalten, Befehle, Testergebnis, offene Punkte, Commit/Branch.
10. **Nach einer Etappe anhalten**, das Ergebnis präsentieren und auf Freigabe zur nächsten Etappe warten.

## Technische Leitplanken
- Home Assistant OS App (Add-on) mit Ingress; Python/FastAPI, schlichtes HTML/CSS/JavaScript, SQLite.
- Backend-Fachlogik unabhängig von Home Assistant ausführbar/testbar halten.
- Python-Pakete reproduzierbar versionieren; SQLite-Migrationen versionieren und testen.
- Geld ausschließlich in Integer-Cent; kein `float` für Buchungs- oder Saldenbeträge.
- Alle Finanzänderungen atomar, referenziell konsistent und auditierbar.
- **Buchung ist Ist; Fälligkeit/Budget/Sparzielzuordnung ist Plan bzw. Reservierung.**
- Keine doppelte Ausgabenerfassung durch Fahrzeuge, Reparaturen oder Projekte.
- Gemeinschaftskonto wird *nicht* verwaltet; Haushaltsbeitrag ist eine normale Ausgabe.
- HTML-UI responsiv, deutsch, EUR, Europe/Berlin, automatisches Hell-/Dunkel-Theme.
- Persistente App-Daten nur im HA-App-`/data`-Bereich; keine privaten Daten im Repository.
- Authentifizierung und Autorisierung mit Ingress sorgfältig prüfen; keine ungeschützten direkten API-Ports.
- Keine externen Dienste für Kernfunktionen.

## Test- und Abnahme-Gates
Jede Etappe muss mindestens haben:
- reproduzierbare lokale Start- und Testbefehle;
- automatisierte Unit-/API-Tests für neue Funktionen;
- Migrations- und Rückwärtskompatibilitätsprüfung, sobald DB-Schema existiert;
- negative/ungültige Eingaben und relevante Grenzfälle;
- Regressionstests des bestehenden Funktionsumfangs;
- dokumentiertes Testresultat in `docs/PROGRESS.md`.

Besonders testen: atomare Transfers, Split-Summen, Refund-Zuordnungen, keine Doppelzählung, Kalender-/Gehaltsmonate, Monatsbudget vs. Liquidität, zwölfmonatige Fixkostenprognose, Sparziel-Unterdeckung, fehlende Tankdaten, Timer-Neustart, Erinnerungs-Nachholung und Backup-Restore.

Falls HA OS, Raspberry Pi oder ein Emulator nicht zur Verfügung stehen: lokale Tests ausführen, **Integrationsprüfung ausdrücklich als nicht durchgeführt markieren**; nicht behaupten, dass die App dort bereits funktioniert.

## Sicherer Aufgabenabschluss
Liefere für **jede** Etappe eine knappe Checkliste: [x] implementiert, [x] Tests lokal, [ ] HA-Laufzeittest sofern ausstehend, [ ] Nutzerfreigabe für nächste Etappe.
Beginne zunächst mit **Etappe 0.1: Repository-Struktur, lokale Startbarkeit, minimaler Health-Endpunkt und Test-Harness**, noch **keine Finanzlogik**. Gehe anschließend nur auf ausdrücklichen Auftrag weiter.

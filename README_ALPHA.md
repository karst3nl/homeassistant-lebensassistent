# Codex starten

Repository: `karst3nl/homeassistant-lebensassistent`  
Branch: **`alpha`** (Pflicht; `main` nicht verändern).

Lies in dieser Reihenfolge:
1. `AGENTS.md` — zwingende Verhaltensregeln, Commit- und Testgates
2. `docs/PFLICHTENHEFT.md` — anonymisierte Anforderungen und logisches Datenmodell
3. `docs/IMPLEMENTATION_PLAN.md` — kleine Implementierungsetappen
4. `docs/PROGRESS.md` — aktueller Stand
5. `docs/ARCHITEKTUR.md` — Systemgrenzen

## Erste Aufgabe
Nur Etappe **0.1** umsetzen: minimales lokal startbares FastAPI-Grundgerüst, GET `/health`, Test-Harness, pytest-Test für Health, reproduzierbare Setup-/Testanleitung. Tests tatsächlich ausführen und dokumentieren. Keine Finanzmodule, keine fiktiv fertig gemeldete HA-Integration.

Vor Commit `git diff --cached` und Datenschutz prüfen. Nur `alpha` committen und pushen. `docs/PROGRESS.md` aktualisieren. Danach stoppen, Ergebnisse/Testbefehle/Commit-SHA berichten und Freigabe abwarten.

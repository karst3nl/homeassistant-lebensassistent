# Lebensassistent — Pflichtenheft v1.0 (anonymisierte Repository-Fassung)

**Status:** Verbindliche fachliche Grundlage. **Keine echten privaten Daten**. Vollständige technische Detailgestaltung (API und Migrationen) erfolgt kontrolliert in Etappen. Sprache Deutsch, EUR, Europe/Berlin.

## 1. Vision und Scope
Lokale, offline-fähige Home-Assistant-App zur Verwaltung von Finanzen, regelmäßigen Kosten, echten Sparzielen, Fahrzeugen/Tankbuch, Projekten/Materialien, Aufgaben, Arbeitszeiten, Kalender, Erinnerungen und Berichten.

**In V1:** acht Module: Dashboard; Konten/Buchungen; Fixkosten/Finanzplanung; Sparziele; Fahrzeuge; Projekte; Zeitmanagement; Systemeinstellungen/Backups/Exports.

**Nicht in V1:** Bank-API, Konten-CSV-Import, Datei-/Beleganhänge, PDF-Generator, KI-Chat, automatische Banküberweisungen, Mehrbenutzersystem, vollständige Verwaltung von Gemeinschaftskonten und Partnerzahlungen, Projektkostenbudget, verschachtelte Aufgaben, eigener täglicher Backup-Scheduler, monetäre Bewertung von Eigenleistung.

## 2. Verbindliche Produktentscheidungen (E01–E38)
| ID | Regel |
|---|---|
| E01 | Kontosaldo nur aus Anfangssaldo + gebuchten Bewegungen, nicht frei überschreibbar |
| E02 | Wiederkehrende Fälligkeiten eindeutig automatisch zuordnen; Mehrdeutigkeit bestätigen lassen |
| E03 | Sparen zählt nur auf tatsächlich verwalteten echten Sparkonten |
| E04 | Mehrere Ziele teilen sich ein Sparkonto mit eindeutigen Guthabenanteilen |
| E05 | Abbuchungen trotz Ziel-Unterdeckung buchen; Zuordnung zur Prüfung markieren |
| E06 | Buchungserfassung manuell; Kontoimport später |
| E07 | Privat, ein Benutzer über Home Assistant |
| E08 | Überweisung zum nicht verwalteten Gemeinschaftskonto = echte Haushaltsausgabe |
| E09 | Keine Kontobewegungen anderer Haushaltsmitglieder erfassen |
| E10 | Fixkostenkonto: Überweisungsbetrag empfehlen, niemals automatisch überweisen |
| E11 | Normalbuchung nur Betrag, Konto, Kategorie Pflicht; Notiz optional; Datum default heute |
| E12 | Eine Buchung auf Kategorien, Fahrzeuge und Projekte anteilig verteilen |
| E13 | Rückerstattung an Original koppeln, proportionale Verteilung vorschlagen, editierbar |
| E14 | Keine Beleganhänge in V1 |
| E15 | Bankabgleich zeigt Differenz ohne Korrekturbuchung |
| E16 | Tankbuch Pflicht nur Fahrzeug, Gesamtbetrag, Konto; Liter/Kilometer optional |
| E17 | Tankpreis flexibel aus Liter+Gesamtbetrag oder Liter+Literpreis |
| E18 | Reparaturteile/Arbeitszeit dokumentieren; Kosten nur aus verknüpften Buchungen |
| E19 | Unbegrenzt Fahrzeuge, archivieren, Verbrauch/Kosten/km bei ausreichenden Daten |
| E20 | Individuelle Erinnerungen zu HU, Versicherung, Steuer, Service |
| E21 | Projekte nur tatsächliche Kosten, keine Projekt-Budgetlimits |
| E22 | Server-Timer und manuelle Zeiten; eigene Stunden nicht monetarisieren |
| E23 | Aufgaben mit Datum/Uhrzeit im Wochenkalender |
| E24 | Fortschritt aus erledigten / aktiven Aufgaben berechnen |
| E25 | Materiallisten pro Projekt, optionale HA-Aufgabenerinnerungen |
| E26 | Dashboard-Widgets ein-/ausblenden/umordnen, Budget prominent |
| E27 | Schnellaktionen: Ausgabe, Einnahme, Umbuchung, Tanken, Timer, Aufgabe |
| E28 | Reminder je Ereignis konfigurierbar; verpasste relevante Hinweise nachholen |
| E29 | Wochenübersicht, Wochentag/Uhrzeit konfigurierbar |
| E30 | CSV-Export und druckfreundliche HTML-Berichte |
| E31 | Hell-/Dunkel-Modus automatisch passend zu HA |
| E32 | Monatsbudget und sofort verfügbare Liquidität getrennt |
| E33 | Kalender- und Gehaltsmonat (einstellbarer Periodenstart) |
| E34 | Standardgehalt als Planwert, Sonderzahlung erst beim tatsächlichen Eingang |
| E35 | Einstellbarer Liquiditätshorizont, default bis nächstes geplantes Gehalt |
| E36 | Fixkostenprognose rollierend 12 Monate, kurzfristige Lücken separat |
| E37 | Nach HA-Neustart Timerprüfung; Nutzer entscheidet Unterbrechungszeit |
| E38 | HA-Backups plus manueller konsistenter Export/Restore |

## 3. Zentrale Geschäftsregeln
- **Single source of truth:** nur Transaktionen und Splits zählen als echte Einnahmen/Ausgaben. Pläne, Materiallisten, Servicepositionen und Sparzuordnungen bewegen niemals Geld.
- Beträge in **integer Cent**, keine Gleitkommafinanzarithmetik; skaliert für Kraftstoff-/Materialmengen.
- Buchungen positiv mit `kind` als Vorzeichenrichtung; nur `posted` in Salden. Auditierbare Stornierung/Korrektur, kein stilles Löschen.
- Einfache Ausgabe hat exakt eine Konto-Buchung; Splits summieren centgenau zum Buchungsbetrag.
- Interner Transfer = zwei gleich hohe, atomare Konto-Buchungen; Gesamtsaldo eigener Konten unverändert, kein Einkommen/Ausgabe.
- Die Zahlung zum nicht verwalteten Gemeinschaftskonto ist keine interne Umbuchung.
- Refund ist neuer Geldeingang mit Original-Split-Verknüpfungen, vorschlagsweise anteilig verteilt und bei Bedarf verändert; netto den ursprünglichen Ausgaben zuordnen. Übererstattung warnen.
- Fixkostenregel/Fälligkeit ≠ Zahlung; Zahlungen eindeutig matchen oder Nutzerentscheidung. Bereits eingeplante Fixkosten nicht bei Zahlung erneut im Budget abziehen.
- Eine Sparzielzuordnung darf in Normalzustand je Konto zusammen nicht mehr als das echte gedeckte Guthaben umfassen; nach Abhebung darf temporär `review_required` entstehen, nie fiktives Guthaben.
- Fahrzeug-/Projektzuordnungen referenzieren Buchungs-Splits und addieren diese innerhalb ihrer jeweiligen Dimension höchstens einmal; dokumentierte Reparaturteile oder Materialstatus sind keine Extraausgabe.
- Arbeitsstunden zählen als Zeit, nicht als Euro-Ausgabe. Maximal ein aktiver Timer; Neustart → manueller Review, keine ungeprüfte bestätigte Zeit.

## 4. Berechnungen

### 4.1 Kontostand
`Saldo(a,t) = Anfangssaldo(a) + Σ gebuchte signed Bewegungen auf a bis t`.
`income, transfer_in, refund_in` positiv, `expense, transfer_out` negativ; `voided` ausgeschlossen. Der Startzeitpunkt muss zu Anfangssaldo und Historie passen.
Bankabgleich: `Differenz = eingetragener Banksaldo - berechneter Stichtagssaldo`. Keine automatische Korrektur.

### 4.2 Kalender-/Gehaltsmonat
Kalendermonat 1. bis Monatsende. Gehaltsmonat Starttag konfigurierbar (Default 15), halboffenes Intervall; kürzere Monate definiert behandeln, keine überlappenden Intervalle. Umschalten erzeugt keine Buchungen.

### 4.3 Rest-Monatsbudget
`BudgetRest(P)=GeplantesEinkommen(P) - geplante laufende Fixkosten(P) - zusätzlicher nicht bereits berücksichtigter Rücklagenbedarf(P) - geplante Sparrate(P) - variable Netto-Ist-Ausgaben(P)`.

Regeln: geplante Fixkosten beim Buchen durch Ist abgleichen statt doppelt abziehen; bereits in fixen Aufwendungen enthaltene Beträge nicht erneut in Rücklagen; Umbuchung auf eigenes Spar-/Fixkostenkonto ist keine Ausgabe, beeinflusst gegebenenfalls planmäßig reserviertes Budget, nicht zusätzlich den Ist-Aufwand. Sonderzahlungen erst in Ist, niemals automatisch im Standardplan. Negative Werte nicht auf null kappen. Plan/Ist/Abweichung getrennt anzeigen.

### 4.4 Sofort verfügbare Liquidität
Horizont `H` einstellbar, Standard nächster erwarteter Gehaltstermin. Berücksichtige **nur heute vorhandene Kontoguthaben**, abzüglich gedeckter Zielzuordnungen sowie **noch ungedeckter** Verpflichtungen bis H. Bereits in separaten Fixkostenbeständen abgedeckte Zahlungen nicht doppelt abziehen. Nicht gebuchte zukünftige Gehälter dürfen den Sofort-Wert nicht erhöhen. Negative Deckungslücke anzeigen; Prognose zukünftiger Zuflüsse separat.

### 4.5 Fixkostenkonto – rollierende 12 Monate
`PrognoseSaldo(t,x)=K0 + Anzahl_geplanter_Überweisungen_bis_t * x + gesicherte_sonstige_Eingänge_bis_t - erwartete_Zahlungen_bis_t`.
Gesucht ist der kleinste centgenaue monatliche Überweisungsbetrag `x >= 0`, der zu allen prognostizierten Fälligkeitsterminen nicht-negative Deckung ergibt. Falls vor dem nächsten möglichen Transfer ein Defizit entsteht: sofortige Deckungslücke separat melden (keine unmögliche Rate erfinden). Bereits erfasste Zahlungen und Ist-Saldo berücksichtigen. Empfehlung erzeugt keinen Transfer.

### 4.6 Fahrzeugstatistik
Netto-Fahrzeugkosten = eindeutige zugeordnete Ausgabe-Splits minus zugehörige Refunds. Kraftstoffverbrauch nur aus nachweislich vollständigen Tankintervallen mit belastbarer Kilometerstrecke; Teilbetankungen innerhalb geeigneter Intervalle aggregieren. Kosten/km nur bei nachvollziehbarem Messzeitraum und ausreichenden Daten; sonst „nicht berechenbar“.

### 4.7 Projektfortschritt
`100 * Anzahl_done / Anzahl_aktiver_Aufgaben` (abgebrochene/archivierte Aufgaben nicht mitzählen). Ohne Aufgaben „keine Aufgaben“. Nur bestätigte Zeit in Stundenstatistiken.

## 5. Logisches Datenbankschema (36 Tabellen)
Default für Entitätstabellen: `id INTEGER PRIMARY KEY`, `created_at`, `updated_at`; FKs mit aktiver referenzieller Integrität, keine Kaskadenlöschung historischer Finanzbuchungen, UTC-Zeitstempel, lokale Darstellung Europe/Berlin. `NULL` heißt unbekannt, nie automatisch null Euro/Liter.

### System (4)
- `app_settings`: key PK, value_json, updated_at — typisierte Konfiguration
- `dashboard_widgets`: id, widget_type, position, visible, config_json, timestamps
- `audit_log`: id, entity_type, entity_id, action, before_json, after_json, reason, occurred_at
- `backup_history`: id, backup_label, created_at, status, schema_version, checksum_sha256, size_bytes, error_summary

### Finanzen (7)
- `accounts`: id, name, account_type, role, opening_balance_cents, opening_date, is_active, include_in_liquidity, sort_order, notes, timestamps
- `categories`: id, name, parent_id FK categories?, kind income/expense, is_active, sort_order, timestamps
- `transactions`: id, account_id FK, kind [income/expense/transfer_in/transfer_out/refund_in], amount_cents (>0), booked_date, description?, payee?, status posted/voided, origin, void_reason?, timestamps
- `transaction_splits`: id, transaction_id FK, category_id FK?, amount_cents (>0), memo?, sort_order, created_at
- `transfers`: id, out_transaction_id FK unique, in_transaction_id FK unique, transfer_date, created_at
- `refund_links`: id, refund_transaction_id FK, original_split_id FK, refund_amount_cents, created_at
- `account_reconciliations`: id, account_id FK, statement_date, recorded_at, statement_balance_cents, calculated_balance_cents, difference_cents, note?

### Fixkosten/Budgets (5)
- `recurring_rules`: id, name, kind, amount_cents, category_id FK, account_id FK, frequency, interval_count, anchor_date, start_date, end_date?, due_adjustment, vehicle_id FK?, active, timestamps
- `recurring_occurrences`: id, rule_id FK, due_date, expected_amount_cents, status, manual_override, note?, timestamps; duplicates prevent
- `occurrence_payments`: id, occurrence_id FK, transaction_split_id FK, allocated_cents, matched_by, created_at
- `budget_plans`: id, period_mode, period_start, period_end_exclusive, planned_income_cents, planned_savings_cents, notes?, timestamps
- `budget_items`: id, budget_plan_id FK, category_id FK?, item_type, planned_cents, recurring_rule_id FK?, notes?

### Sparen (3)
- `savings_goals`: id, name, target_cents, target_date?, priority, status, description?, timestamps
- `goal_allocations`: id, goal_id FK, account_id FK, allocated_cents, coverage_status, timestamps; unique(goal_id,account_id)
- `goal_allocation_events`: id, allocation_id FK, old_cents, new_cents, reason?, occurred_at

### Fahrzeuge (6)
- `vehicles`: id, name, manufacturer?, model?, license_plate?, model_year?, fuel_type?, status, opening_odometer_km?, notes?, timestamps
- `fuel_entries`: id, vehicle_id FK, transaction_id FK unique, filled_at, total_paid_cents, liters_milli?, unit_price_milli_cents?, odometer_km?, full_tank?, notes?, timestamps
- `vehicle_service_events`: id, vehicle_id FK, event_type, event_date, odometer_km?, description, notes?, status, timestamps
- `vehicle_service_items`: id, service_event_id FK, item_type, description, quantity_milli?, unit?, unit_price_cents?, labor_minutes?, sort_order
- `vehicle_cost_links`: id, vehicle_id FK, service_event_id FK?, transaction_split_id FK, allocated_cents, created_at
- `vehicle_reminders`: id, vehicle_id FK, title, reminder_type, due_date?, due_odometer_km?, lead_time_minutes, enabled, status, timestamps

### Projekte & Planung (8)
- `projects`: id, name, description?, status, timestamps, archived_at?
- `project_tasks`: id, project_id FK, title, description?, priority, status, estimated_minutes?, due_at?, completed_at?, timestamps
- `time_entries`: id, project_id FK, task_id FK?, started_at, ended_at, duration_seconds, origin, status, note?, timestamps
- `active_timers`: id, project_id FK, task_id FK?, started_at, last_resumed_at?, accumulated_seconds, paused_at?, state, review_reason?, updated_at
- `schedule_blocks`: id, task_id FK, starts_at, ends_at, status, note?, timestamps
- `project_materials`: id, project_id FK, task_id FK?, name, quantity_milli, unit, status, note?, timestamps
- `project_material_links`: id, material_id FK, transaction_split_id FK, allocated_cents, created_at
- `project_cost_links`: id, project_id FK, transaction_split_id FK, allocated_cents, created_at

### Notifications (3)
- `reminder_rules`: id, source_type, source_id, lead_time_minutes, enabled, timestamps
- `notification_queue`: id, event_key unique, reminder_rule_id FK?, due_at, status, attempt_count, last_attempt_at?, sent_at?, error?
- `notification_settings`: id, target_service, weekly_day (1..7), weekly_time, weekly_enabled, notifications_enabled, updated_at

**Konsistenz:** Die 36 Tabellen sind logisches Ziel; Migrationen dürfen technische Hilfstabellen ergänzen. Auf geteilte Geldanteile und Kostenlinks gelten Summenobergrenzen je Buchungs-Split und je Auswertungsdimension. Alle FK-/Unique-/Check-Constraints und Indizes bei Migration konkretisieren und testen.

## 6. Screens und UX
- Startseite: Monatsbudget groß, sofort verfügbar separat, Konten, nächste Fixkosten, Sparziele, Projektfortschritt, Termine; Widgets sichtbar/unsichtbar und sortierbar.
- Finanzansicht: Buchungsliste, Suche, Kategorien, Splits, Refunds, Monatsansichten, Konten und Abgleich.
- Fixkosten: monatlich/jährlich, Fälligkeiten bezahlt/offen, 12-Monats-Kurve, Überweisungsempfehlung und Sofortlücken.
- Sparziele: echte Sparkonten, Zuordnung und Deckungsstatus, Fortschritt, Unterdeckungsreview.
- Fahrzeuge: Profile, Tank-Schnellerfassung, vollständige Tankhistorie, Service/Teile/Stunden, Kosten und Reminder.
- Projekte: Projektliste, Aufgaben, Prioritäten, Materialliste, Kosten, Fortschritt.
- Kalender: Wochen- und mobile Tagesansicht, Planung nach Datum/Uhrzeit, Timer und Zeitjournal.
- Einstellungen: Konten/Kategorien, Standardgehalt, Starttag Gehaltsmonat, Liquiditätshorizont, Notifications, Backup, CSV-/HTML-Export.
- Globale Schnellaktionen: Ausgabe, Einnahme, Umbuchung, Tanken, Timer, Aufgabe.
- Responsive Desktop/iPhone/iPad, Tastaturbedienung, zugängliche Formulare, Hell/Dunkel aus Home Assistant.

## 7. Home Assistant / Technik / Datenschutz
- Home Assistant OS Add-on/App über Supervisor mit Ingress, **keinen offenen ungeschützten externen Port**.
- Backend Python/FastAPI; Frontend plain HTML/CSS/JS; SQLite mit WAL/FKs; Build ARM-kompatibel für Zielgerät.
- Ingress-URL-Prefix und Proxy-Header berücksichtigen; Authentifizierung und Zugriffsschutz testen, keinerlei öffentliche Buchungsendpunkte.
- Laufzeitdaten/DB/Backups nur in persistentem App-`/data`-Bereich, nicht ins Git-Arbeitsverzeichnis.
- Lokale Kernfunktionen ohne Cloud; keine Telemetrie; keine Finanzwerte in Standardlogs.
- HA-Notifications und wöchentliche Zusammenfassung über persistente Queue mit Ereignisschlüssel, relevanzgeprüfter Nachholung nach Neustart. Doppelte Zustellung nach Crash nicht vollständig ausschließbar.
- HA-Backups plus manueller SQLite-konsistenter Export/Restore, Checksum und Datenbankintegritätsprüfung, defekte Backups verweigern, vor Restore vorhandenen Zustand sichern.
- Fehlerfälle (FK, negative Beträge, DST, Neustart, Inkonsistenzen, Deadlines, Ausfall) ausdrücklich testen.

## 8. Abnahmetests — Mindestmatrix
| Test | Erwartung |
|---|---|
| Ledger: 100 EUR interner Transfer | Gesamtsaldo unverändert |
| Ledger: 100 EUR Split 70/30 | ein Geldabfluss; Kategorien 70/30 |
| Ledger: inkonsistenter Split | vollständig atomar abgelehnt |
| Refund: 30 EUR auf 100 EUR | 70 EUR Nettoaufwand, Zuordnung passt |
| Abgleich: Banksaldo abweichend | Differenz, keine automatische Buchung |
| Haushaltsbeitrag auf externes Konto | echte Ausgabe |
| Fixkostenplan bezahlt | Match, keine doppelte Budgetminderung |
| Budget: Plan/Ist, Sonderzahlung | Sonderzahlung nicht in Standardplan |
| Periode: Kalender-/Gehaltsmonat | vollständige, disjunkte Zuordnung |
| Liquidität: zukünftiges Gehalt | zählt nicht als heutiges Geld |
| Prognose: Fälligkeit vor Transfer | explizite sofortige Lücke |
| Sparkonto: Zielverteilung | keine Doppelbelegung gedeckten Guthabens |
| Sparkonto: Auszahlung unterdeckt Ziele | Buchung erlaubt, Review erforderlich |
| Fahrzeug: Tanken nur 3 Pflichtfelder | Finanzbuchung und Tankdatensatz |
| Fahrzeug: fehlende Liter/km | Verbrauch nicht berechenbar |
| Reparatur: 2 Teile, 1 Rechnung | ein finanzieller Kostenbetrag |
| Projekt: 8/20 Aufgaben | 40% Fortschritt |
| Projekt: Material gekauft markieren | keine automatische Buchung |
| Timer: Browser schließen | serverseitiger Zustand bleibt |
| Timer: HA-Neustart | manuelle Prüfung vor Stundenbestätigung |
| Notification: überfällig nach Neustart | nur noch gültige Events nachholen |
| Backup: defektes Archiv | Restore verhindert, vorhandene DB bleibt |
| Update: Migration | Konten/Buchungen bleiben vollständig |
| Ingress: nicht autorisierte Anfrage | kein Zugriff auf Finanzdaten |
| Öffentlichkeit: Commits/Tests | keine realen persönlichen Daten |

Alle weiteren Randfälle aus der jeweiligen Implementierungsetappe ergänzen, bestehende Tests immer erneut laufen lassen.

## 9. Umsetzung und Freigabe
Die schrittweise Entwicklung und ihre Gates stehen verbindlich in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Codex muss [AGENTS.md](../AGENTS.md) befolgen.

**Nur Branch `alpha`**, kleine Etappen, nach jeder Etappe Tests + Ergebnisbericht + Freigabepause. **`main` nicht anfassen und nie eigenständig mergen.** Erst nach komplettem V1-Release-/Integrations-/Privacy-Check entscheidet der Nutzer über den Merge.

# Lebensassistent Alpha — HA-App

Experimentelle Basisoberfläche mit Navigation, automatischem Browser-Theme und
Health-Endpunkt. Version **0.0.4** bietet die ersten bedienbaren Konten- und
Kategorienmasken mit SQLite und Audit. Buchungen, Projekte und Erinnerungen
sind noch nicht implementiert. Die Verpackung wurde lokal mit Docker auf **amd64** geprüft.
Der Nutzer hat die Installation und erste Sichtprüfung von **0.0.1** auf seinem
Home Assistant bestätigt. **Die 403-Korrektur auf HA, vollständige HA-Security-/
Restart-Prüfungen und ARM-Nachweise stehen noch aus.**

## Installation zur HA-Prüfung

In Home Assistant unter **Einstellungen → Apps → App-Store → Repositories**
dieses Repository mit explizitem Entwicklungsbranch hinzufügen:

```text
https://github.com/karst3nl/homeassistant-lebensassistent#alpha
```

`#alpha` ist erforderlich. Der Homepage-Link in `repository.yaml` bestimmt
nicht den geklonten Branch. Die App wird aus dem Quellcode auf `alpha` gebaut;
es gibt noch kein veröffentlichtes Container-Image.

Nach Aktualisierung des Stores **Lebensassistent Alpha** installieren, starten
und **Weboberfläche öffnen** wählen. Die Seitenleiste ist für Administratoren
konfiguriert. Automatischer Start ist zunächst ausgeschaltet, kann in HA
aktiviert werden. Diese Schritte sind die Anleitung für den noch offenen
weiteren HA-Abnahmetest; die bisherige Nutzerbestätigung umfasst Installation
und erste Sichtprüfung von 0.0.1.

## Update von 0.0.1 bis 0.0.3 auf 0.0.4

Die Repositories im App-Store aktualisieren und das angebotene Update auf
**0.0.4** installieren. Der Branch bleibt **`#alpha`**. Die Datenbank wird beim
Start auf Schema 2 gebracht. Bestehende Audit-Daten bleiben erhalten;
bestehende Konten und Kategorien aus 0.0.3 bleiben erhalten. Bei älteren
Versionen werden die Konten-/Kategorientabellen leer angelegt. Es werden keine
Beispieldaten angelegt.

Nach dem Update Start, Weboberfläche und einen Restart auf HA prüfen. Version
0.0.4 wurde lokal gebaut und auf Bedienung, Start und Persistenz geprüft; das Update auf
dem HA-System steht noch aus.

Version 0.0.4 korrigiert den gemeldeten **403 beim Kontoanlegen** unter Ingress.
Nach dem Update die alte Add-on-Weboberfläche schließen und über Home Assistant
frisch öffnen. Die Korrektur gilt auch für Kategorien und Archivieren/Aktivieren.
Eine Bestätigung auf dem HA-System steht noch aus.

## Erste Funktionen testen

Im Menü **Konten & Buchungen** sind jetzt **Konten & Kategorien** verfügbar.
Für die Alpha-Prüfung ausschließlich synthetische Daten verwenden:

1. Unter **Neues Konto** einen Testnamen, eine Kontoart, einen Anfangssaldo und
   das Startdatum eingeben. Eine Notiz ist optional. **Konto anlegen** wählen.
2. Eurobeträge ohne Tausendertrennzeichen eingeben, z. B. `1234,56`, `12.34`
   oder `-12,34`. Höchstens zwei Nachkommastellen sind zulässig. Ein negativer
   Anfangssaldo ist erlaubt; das Startdatum muss ein echtes Kalenderdatum sein.
3. Das Konto **archivieren** und danach **aktivieren**. Es wird nicht gelöscht;
   Anfangssaldo und Startdatum bleiben nach der Anlage unverändert.
4. Unter **Neue Kategorie** einen Namen und **Einnahme** oder **Ausgabe** wählen.
   Optional eine aktive Oberkategorie derselben Art auswählen.
5. Auch Kategorien archivieren/aktivieren. Aktive Unterkategorien müssen zuerst
   archiviert werden; eine Unterkategorie kann erst nach ihrer Oberkategorie
   wieder aktiviert werden.
6. Seite neu laden und die App in HA neu starten; Testeinträge sollten erhalten
   bleiben. Das ist auf dem HA-System noch zu bestätigen.

Die Masken zeigen Validierungsfehler an und behalten eingegebene Werte zur
Korrektur. Bei einem falschen Anfangssaldo kann das Testkonto in dieser Version
archiviert und neu angelegt werden; eine direkte Saldoänderung ist nicht
vorgesehen. Es gibt noch keine Bearbeitung von Namen/Notizen, keine Löschung
und keine Buchungserfassung. Die angezeigten Werte sind **Anfangssalden**,
noch keine aus Buchungen berechneten Kontostände.

Nach Update oder Neustart alte offene Formularseiten neu laden. Sollte eine
alte Seite „Anfrage nicht zulässig“ anzeigen, neu laden und erneut versuchen.

## Einstellungen, Netzwerk und Daten

- Es gibt noch keine App-Optionen. `options` und `schema` sind leer.
- Der interne Serverport **8099** wird ausschließlich über Ingress genutzt.
  Es werden keine Hostports, Host-Netzwerkzugriffe oder zusätzlichen
  Supervisor-/HA-/Docker-API-Berechtigungen beantragt. Schutzmodus bleibt an.
- Nur der echte TCP-Peer des Supervisors (`172.30.32.2`) wird akzeptiert.
  `X-Forwarded-For` kann diese Prüfung nicht ersetzen. Erst danach wird genau
  ein gültiger `X-Ingress-Path` ausgewertet. Direkte Aufrufe, auch aus dem
  Container über Loopback, liefern **403**; es gibt keine Health-Ausnahme.
- Die HA-Anmeldung wird durch Home Assistant/Supervisor geprüft. Der Adapter
  ersetzt deren Sessionprüfung nicht. Die echte Vertrauenskette wurde noch
  nicht auf HA OS getestet.
- Private Laufzeitdaten gehören ausschließlich in das automatisch von HA
  bereitgestellte **`/data`**. Der Startprozess bereitet nur dieses Verzeichnis
  mit Eigentümer UID/GID **1000** und Modus **0700** vor. Danach verwirft er
  Root-Rechte und prüft als unprivilegierter Benutzer die Schreibbarkeit.
  Vorhandene Dateien werden dabei weder rekursiv verändert noch gelöscht.
- Die Datenbank liegt unter **`/data/lebensassistent.sqlite3`**; zugehörige
  WAL-/SHM-Dateien bleiben im selben privaten Verzeichnis. Verbindungen
  aktivieren Fremdschlüssel, WAL und vollständige Synchronisierung.
- Schemaänderungen, Konten-/Kategorienänderungen und ihre Audit-Einträge werden
  jeweils gemeinsam atomar angewandt.
  Unbekannte neuere oder veränderte Migrationshistorien sowie beschädigte
  Dateien verhindern den Start. Vorhandene Daten werden nicht still gelöscht
  oder durch eine neue leere Datenbank ersetzt.
- Die lokale Persistenzprüfung verwendet synthetische Konten, Kategorien,
  Audit-Einträge und Marker. Sie ist kein Backup-/Restoretest. Das Audit-Protokoll ist durch
  SQLite-Trigger gegen reguläres Ändern/Löschen geschützt, nicht gegen einen
  Angreifer mit direktem Dateizugriff.
- HTTP-Access-Logs sind ausgeschaltet, damit Ingress-Sessionpfade nicht in
  Standardlogs gelangen.

Die Oberfläche folgt der Browser-/Systemeinstellung für Hell/Dunkel. Eine
abweichende manuelle HA-Theme-Einstellung ist noch nicht synchronisiert.

## Offene HA-Abnahme

Auf einem Entwicklungs-HA-System ausschließlich synthetische Daten verwenden:

1. Installation und Start aus `#alpha` prüfen; UI und Assets über Ingress öffnen.
2. Anmeldung/Abmeldung und einen nicht angemeldeten Browser prüfen. Ohne gültige
   HA-Session darf kein Zugriff über Ingress möglich sein.
3. Navigation, Fehlerseiten, Präfixe und HTTPS-Redirects prüfen.
4. Stop, Start und Restart in HA prüfen; danach einen synthetischen Marker in
   `/data` kontrollieren. Auch App-Neuerstellung/Update mit erhaltenen Daten
   separat prüfen, ohne private Daten zu verwenden.
5. Schutzmodus, fehlende Hostports und Prozessrechte kontrollieren.
6. Datenbank und Migrationshistorie nach Update und Restart prüfen, ohne private
   Daten zu verwenden. Den ARM-Build und Betrieb auf dem Zielgerät prüfen.

Ergebnisse in `docs/PROGRESS.md` ergänzen. Etappe 1.2 beginnt erst nach
ausdrücklicher Nutzerfreigabe.

## Lokale Entwicklung und Fehlerdiagnose

[DEVELOPMENT.md](docs/DEVELOPMENT.md) enthält Start-, Build- und Testbefehle.
Ein **403** bei einem direkten Containeraufruf ist beabsichtigt. Ein **400**
vom erlaubten Peer weist auf einen fehlenden, doppelten oder ungültigen
Ingress-Präfix hin. Fehler bei `/data` verhindern den Serverstart.

Bei Problemen nur bereinigte Informationen im
[Repository auf `alpha`](https://github.com/karst3nl/homeassistant-lebensassistent/tree/alpha)
bereitstellen; keine Sessionpfade, Tokens oder privaten Laufzeitdaten posten.

Technische Grundlage:
[HA-Ingress](https://contributors.home-assistant.io/apps/guides/ingress/),
[App-Konfiguration](https://contributors.home-assistant.io/apps/reference/configuration/).

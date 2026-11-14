# Lebensassistent Alpha — HA-App

Experimentelle Basisoberfläche mit Navigation, automatischem Browser-Theme und
Health-Endpunkt. Version **0.0.2** ergänzt die interne SQLite-Grundlage mit
Migrationen und Audit. Konten, Buchungen, Projekte und Erinnerungen sind noch
nicht implementiert. Die Verpackung wurde lokal mit Docker auf **amd64** geprüft.
Der Nutzer hat die Installation und erste Sichtprüfung von **0.0.1** auf seinem
Home Assistant bestätigt. **Das Update auf 0.0.2, vollständige HA-Security-/
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

## Update von 0.0.1 auf 0.0.2

Die Repositories im App-Store aktualisieren und das angebotene Update auf
**0.0.2** installieren. Der Branch bleibt **`#alpha`**. Die bisherige Oberfläche
bleibt bestehen. Beim ersten Start entsteht ausschließlich die technische
Datenbank mit Migrationshistorie und Audit-Protokoll; Konten oder Buchungen
werden noch nicht angelegt. Es gibt in dieser Etappe keine neuen Eingabemasken.

Nach dem Update Start, Weboberfläche und einen Restart auf HA prüfen. Version
0.0.2 wurde lokal gebaut und auf Start und Persistenz geprüft; das Update auf
dem HA-System steht noch aus.

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
- Schemaänderungen und ihre Audit-Einträge werden gemeinsam atomar angewandt.
  Unbekannte neuere oder veränderte Migrationshistorien sowie beschädigte
  Dateien verhindern den Start. Vorhandene Daten werden nicht still gelöscht
  oder durch eine neue leere Datenbank ersetzt.
- Die lokale Persistenzprüfung verwendet nur synthetische Audit-Einträge und
  Marker. Sie ist kein Backup-/Restoretest. Das Audit-Protokoll ist durch
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

Ergebnisse in `docs/PROGRESS.md` ergänzen. Etappe 1.1 beginnt erst nach
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

# Lebensassistent Alpha — HA-App

Experimentelle Basisoberfläche mit Navigation, automatischem Browser-Theme und
Health-Endpunkt. Finanzen, Datenbank, Projekte und Erinnerungen sind noch nicht
implementiert. Die Verpackung wurde lokal mit Docker auf **amd64** geprüft.
**Ein echter HA-OS-/Ingress- oder ARM-Laufzeittest wurde noch nicht ausgeführt.**

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
HA-Abnahmetest, kein Nachweis einer bereits erfolgten Installation.

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
- Aktuell existiert noch keine Datenbank. Die lokale Persistenzprüfung
  verwendet nur einen synthetischen Marker und ist kein Backup-/Restoretest.
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
6. Den ARM-Build und Betrieb auf dem tatsächlichen Zielgerät prüfen.

Ergebnisse in `docs/PROGRESS.md` ergänzen. Etappe 0.4 beginnt erst nach
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

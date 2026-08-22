# Python Tools

A small collection of guided tools for downloading YouTube media and organizing PDF files.
No Python commands are required for normal use: open the starter for your operating system,
choose an action, and answer the displayed questions.

Eine kleine Sammlung geführter Werkzeuge zum Herunterladen von YouTube-Medien und zum
Organisieren von PDF-Dateien. Für die normale Nutzung sind keine Python-Befehle nötig:
Starter öffnen, Aktion auswählen und die angezeigten Fragen beantworten.

## Quick start / Schnellstart

| Operating system / Betriebssystem | Start |
| --- | --- |
| macOS | Double-click / Doppelklick: **`Python Tools.command`** |
| Windows | Double-click / Doppelklick: **`Python Tools.cmd`** |
| Linux | Double-click **`python-tools.sh`** and choose “Run”, or start it from the file manager as a program / Doppelklick und „Ausführen“ wählen |

The first launch automatically creates the dedicated `.python-tools-venv` environment and
installs the required Python packages. Later launches open the menu directly. The starter never
changes the global Python installation or a contributor's separate `.venv`.

Beim ersten Start werden automatisch die eigene Umgebung `.python-tools-venv` und die benötigten
Python-Pakete eingerichtet. Spätere Starts öffnen direkt das Menü. Weder die globale
Python-Installation noch eine separate Entwickler-`.venv` werden dabei verändert.

### Requirements / Voraussetzungen

- Python 3.11 or newer / Python 3.11 oder neuer
- [FFmpeg](https://ffmpeg.org/) for YouTube audio conversion and video merging / für
  YouTube-Audiokonvertierung und das Zusammenführen von Videos
- macOS: `SetFile` for changing PDF creation dates; it is included with the Xcode Command Line
  Tools / zum Ändern des PDF-Erstellungsdatums, enthalten in den Xcode Command Line Tools

The launcher detects a missing FFmpeg installation and shows an appropriate installation
command. Common choices are:

Der Launcher erkennt ein fehlendes FFmpeg und zeigt den passenden Installationsbefehl an.
Übliche Varianten sind:

```bash
# macOS (Homebrew)
brew install ffmpeg

# Debian/Ubuntu
sudo apt install ffmpeg
```

On Windows, use:

```powershell
winget install Gyan.FFmpeg
```

## Language / Sprache

The initial language follows the operating-system locale: German for German locales, English
otherwise. Select **“Language / Sprache”** in the main menu at any time to switch. The choice is
remembered for future launches.

Die anfängliche Sprache richtet sich nach der Systemsprache: Deutsch bei einer deutschen
Systemeinstellung, sonst Englisch. Über **„Sprache / Language“** im Hauptmenü kann sie jederzeit
gewechselt werden. Die Auswahl wird für spätere Starts gespeichert.

## Everything available in the guided menu / Alle Möglichkeiten im einfachen Menü

The guided interface exposes the complete useful feature set. There are no hidden options that
require cryptic terminal commands.

Die geführte Oberfläche stellt den vollständigen sinnvollen Funktionsumfang bereit. Es gibt
keine versteckten Optionen, die kryptische Terminalbefehle voraussetzen.

### YouTube audio / YouTube-Audio

- One or multiple video or playlist URLs / eine oder mehrere Video- oder Playlist-URLs
- MP3, M4A, WAV, or FLAC / MP3, M4A, WAV oder FLAC
- Configurable audio quality / einstellbare Audioqualität
- Selectable output folder / frei wählbarer Ausgabeordner
- Single-video protection or intentional playlist downloads / Schutz vor versehentlichen
  Playlist-Downloads oder bewusstes Herunterladen von Playlists
- Optional detailed diagnostic output / optionale ausführliche Diagnoseausgabe

The friendly defaults produce a 192 kbit/s MP3 in the current user's `Downloads` folder and
download only the selected video.

Die komfortablen Standardwerte erzeugen eine MP3 mit 192 kbit/s im Ordner `Downloads` des
aktuellen Benutzers und laden nur das ausgewählte Video herunter.

### YouTube video / YouTube-Video

- One or multiple video or playlist URLs / eine oder mehrere Video- oder Playlist-URLs
- Best available quality or a maximum resolution such as 1080p / beste verfügbare Qualität oder
  eine maximale Auflösung wie 1080p
- Selectable output folder / frei wählbarer Ausgabeordner
- Single-video or playlist mode / Einzelvideo- oder Playlist-Modus
- Optional detailed diagnostic output / optionale ausführliche Diagnoseausgabe

Existing downloaded files are never overwritten. Filenames contain the title and YouTube ID.

Bereits vorhandene Downloads werden niemals überschrieben. Die Dateinamen enthalten Titel und
YouTube-ID.

Only download media when you have the necessary rights and comply with the service's terms,
copyright law, and local regulations.

Lade nur Medien herunter, für die du die nötigen Rechte besitzt, und beachte die
Nutzungsbedingungen des Dienstes, das Urheberrecht und lokale Vorschriften.

### Rename PDFs / PDFs umbenennen

The tool reads dates and matching keywords from the first pages of each PDF and creates meaningful
filenames. The menu supports:

Das Werkzeug liest Datumsangaben und passende Schlüsselwörter aus den ersten Seiten jeder PDF
und erzeugt aussagekräftige Dateinamen. Das Menü unterstützt:

- One folder or recursive subfolder processing / einen Ordner oder rekursive Verarbeitung
- The bundled or a custom keyword file / die mitgelieferte oder eine eigene Keyword-Datei
- `Date_Title`, `Title_Date`, or a custom format using `{date}` and `{title}` /
  `Datum_Titel`, `Titel_Datum` oder ein eigenes Format mit `{date}` und `{title}`
- Optional detailed output / optionale ausführliche Ausgabe

The guided flow always performs a safe preview first and asks for confirmation before renaming
anything. Filename collisions receive a numeric suffix; existing files are preserved.

Der geführte Ablauf zeigt immer zuerst eine sichere Vorschau und fragt vor jeder Umbenennung
noch einmal nach. Bei Namenskollisionen wird eine Nummer ergänzt; bestehende Dateien bleiben
erhalten.

### Set PDF dates / PDF-Datumswerte setzen

Supported filename patterns / Unterstützte Dateinamen:

- `20260823_Report.pdf`
- `2026-08-23_Report.pdf`
- `Report_20260823.pdf`

The menu accepts multiple folders, optional recursive processing, modification-date updates, and
detailed output. It always previews changes before applying them.

Das Menü akzeptiert mehrere Ordner, optionale rekursive Verarbeitung, die Aktualisierung des
Änderungsdatums und eine ausführliche Ausgabe. Änderungen werden immer zuerst als Vorschau
angezeigt.

- macOS changes the creation date and can additionally change the modification date. /
  macOS ändert das Erstellungsdatum und auf Wunsch zusätzlich das Änderungsdatum.
- Windows changes the creation date and can additionally change the modification date. /
  Windows ändert das Erstellungsdatum und auf Wunsch zusätzlich das Änderungsdatum.
- Linux filesystems generally cannot change creation time, so the guided flow safely updates the
  modification date instead. / Linux-Dateisysteme können die Erstellungszeit normalerweise nicht
  ändern; der geführte Ablauf setzt deshalb sicher das Änderungsdatum.

## Optional command-line reference / Optionale Kommandozeilenreferenz

The same functionality remains scriptable for automation. This section is optional and is not
required for normal use.

Dieselben Funktionen bleiben für Automatisierungen skriptfähig. Dieser Abschnitt ist optional
und für die normale Nutzung nicht erforderlich.

```bash
# Open the complete guided menu / Vollständiges Menü öffnen
.python-tools-venv/bin/python -m projects.launcher

# YouTube video to MP3
.python-tools-venv/bin/python projects/ytVideoDownloader.py --audio --single \
  --output ~/Downloads 'https://www.youtube.com/watch?v=VIDEO_ID'

# Preview PDF renaming / PDF-Umbenennung als Vorschau
.python-tools-venv/bin/python projects/pdfRename.py --dry-run '/path/to/pdfs'

# Preview PDF date changes / PDF-Datumsänderungen als Vorschau
.python-tools-venv/bin/python projects/editCreationDate.py --dry-run '/path/to/pdfs'
```

These examples use the macOS/Linux interpreter path. On Windows it is
`.python-tools-venv\Scripts\python.exe`.

Diese Beispiele verwenden den macOS-/Linux-Pfad. Unter Windows lautet er
`.python-tools-venv\Scripts\python.exe`.

Every individual script supports `--help` for its complete automation interface.

Jedes einzelne Skript bietet mit `--help` seine vollständige Automatisierungsschnittstelle an.

## Development / Entwicklung

Normal users do not need these steps. Contributors should create a separate `.venv`, install the
pinned development tools, and run the verification suite:

Normale Benutzer benötigen diese Schritte nicht. Mitwirkende sollten eine separate `.venv`
erstellen, die festgeschriebenen Entwicklungswerkzeuge installieren und die Prüfungen ausführen:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Runtime packages are pinned in `requirements.txt`; test and lint packages are pinned in
`requirements-dev.txt`.

Die Laufzeitpakete sind in `requirements.txt`, die Test- und Lintpakete in
`requirements-dev.txt` festgeschrieben.

## License / Lizenz

This repository is licensed under the [MIT License](LICENSE.md). Third-party dependencies retain
their own licenses.

Dieses Repository steht unter der [MIT-Lizenz](LICENSE.md). Drittanbieter-Abhängigkeiten behalten
ihre eigenen Lizenzen.

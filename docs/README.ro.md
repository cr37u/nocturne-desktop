# Nocturne

Player de muzică local pentru **Windows** și **Linux**: lipești un link YouTube (video sau playlist),
Nocturne descarcă cel mai bun flux audio și apoi redă totul **offline**.

- Python 3.12 · PySide6 (Qt 6) + Qt Quick/QML · yt-dlp (folosit ca bibliotecă) · QtMultimedia (FFmpeg) · SQLite
- Fără cheie API, fără server, fără ffmpeg extern
- Interfață în **Română** (implicit), **English**, **Русский** — schimbare instantanee, fără repornire

---

## Cuprins

1. [Funcții](#funcții)
2. [Structura proiectului](#structura-proiectului)
3. [Rulare din sursă](#rulare-din-sursă)
4. [Build Windows (.exe + portabil)](#build-windows-exe--portabil)
5. [Ediția completă Windows (MSIX + widget Win+W)](#ediția-completă-windows-msix--widget-winw)
6. [Build Linux (AppImage)](#build-linux-appimage)
7. [Widgeturi Linux (KDE / GNOME)](#widgeturi-linux-kde--gnome)
8. [Actualizarea yt-dlp](#actualizarea-yt-dlp)
9. [Traduceri](#traduceri)
10. [Date, jurnale, depanare](#date-jurnale-depanare)
11. [Listă de test](#listă-de-test)

---

## Funcții

| Zonă | Ce face |
|---|---|
| Adăugare | Linkuri `watch?v=`, `youtu.be`, `music.youtube.com`, Shorts și playlisturi (`list=…`, se iau **toate** elementele). **Ctrl+V** oriunde în fereastră adaugă linkul din clipboard; poți și trage un link din browser peste fereastră. |
| Descărcare | Doar audio (`bestaudio[ext=m4a]/bestaudio[acodec=opus]/bestaudio`), fără post-procesare. 1–8 descărcări în paralel (implicit 4), fragmente concurente, progres + viteză per melodie și global, 3 reîncercări, duplicatele (după id video) sunt sărite. Fișierele merg în `Muzică/Nocturne` (Windows: `%USERPROFILE%\Music\Nocturne`, Linux: `XDG_MUSIC_DIR/Nocturne`). Un playlist YouTube devine automat playlist local. |
| Player | Redă automat următoarea, play/pauză, următoarea, anterioara (repornește dacă ai trecut de 3 s), derulare, amestecare, repetare (oprit / toate / una), volum, favorite, adăugare în playlist, ștergere, coadă reordonabilă prin tragere. Ultima melodie, poziția și coada sunt restaurate la pornire. |
| Tastatură | **Spațiu** play/pauză · **Ctrl+→/←** următoarea/anterioara · **Ctrl+↑/↓** volum · **Ctrl+F** căutare · **Ctrl+V** adaugă link · tastele media ale tastaturii (prin integrarea media a sistemului). |
| Tray | Închiderea ferestrei o ascunde în tray; muzica merge mai departe. Meniu: Arată, Play/Pauză, Anterioara, Următoarea, Widget, Mini-player, Limbă, Ieșire. |
| Windows | Controale media în flyout-ul de volum și pe ecranul de blocare (SMTC: titlu, artist, copertă, butoane, derulare) · butoane anterioara / play-pauză / următoarea în previzualizarea din taskbar (pictograma se schimbă live) · progresul descărcărilor pe pictograma din taskbar · notificare toast când se termină un playlist · „Pornește cu sistemul”. |
| Linux | MPRIS2 (`org.mpris.MediaPlayer2.nocturne`): widgeturile media GNOME/KDE, ecranul de blocare și tastele media · notificări desktop · fișier `.desktop` + iconițe · autostart XDG. |
| Widgeturi | Widget desktop (card mare 360×140 sau „pastilă” 300×60, se poate trage, ține minte poziția, „Mereu deasupra”, „Fixează pe desktop”), mini-player 380×176 mereu deasupra, widget Win+W (ediția MSIX), plasmoid KDE, extensie GNOME. |

---

## Structura proiectului

```
nocturne/                     pachetul aplicației
  __main__.py                 python -m nocturne
  app.py                      pornire: Qt, servicii, motor QML, tray, integrare OS
  app_controller.py           „App” în QML: navigare, bibliotecă, setări
  player.py                   QMediaPlayer + coadă, amestecare, repetare, persistență
  downloader.py               yt-dlp: analiză link, descărcări paralele, reîncercări
  db.py  settings.py  models.py  links.py  i18n.py  icons.py  tray.py  ytdlp_update.py
  platform/
    base.py                   interfața comună (MediaControls, Taskbar, Autostart, notificări)
    windows.py                SMTC (winrt), ITaskbarList3 (comtypes), toast, Run key / StartupTask
    linux.py                  MPRIS2 + notificări prin D-Bus, autostart XDG, instalare plasmoid
    widget_ipc.py             server pe \\.\pipe\nocturne pentru puntea Win+W
  qml/Nocturne/               interfața (Theme.qml = toate tokenurile de design)
  assets/                     fonturi Manrope (OFL), iconițe
  i18n/                       nocturne_{ro,en,ru}.ts (sursă) și .qm (compilat)
widget-bridge/                C# .NET 8 — furnizor de widget Windows 11 (IWidgetProvider)
packaging/
  nocturne-windows.spec  nocturne-linux.spec  pyinstaller_common.py  launcher.py
  build_windows.ps1  nocturne.iss  innosetup/Romanian.isl
  msix/AppxManifest.xml  msix/build_msix.ps1  msix/Assets/
  build_linux.sh  linux/ (AppRun, .desktop, metainfo, iconițe)
  flatpak/io.github.nocturne.yml
  plasmoid/io.github.nocturne.widget/
  gnome-extension/nocturne@nocturne/
tools/
  make_assets.py              generează .ico, PNG-uri, logo-uri MSIX, resursa de versiune
  i18n_tool.py                update / release / check pentru traduceri (Qt Linguist)
  translations_seed.py        traducerile inițiale RO/EN/RU
.github/workflows/build.yml   CI: .exe + .zip + .msix pe Windows, AppImage pe Linux
UI/                           machetele de design (HTML + PNG)
```

---

## Rulare din sursă

Ai nevoie de **Python 3.12**.

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python tools\i18n_tool.py release      # compilează traducerile (.qm)
.\.venv\Scripts\python -m nocturne
```

**Linux**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/i18n_tool.py release
.venv/bin/python -m nocturne
```

Pe Linux, Qt 6.5+ are nevoie de `libxcb-cursor0` (Debian/Ubuntu) / `xcb-util-cursor` (Fedora/Arch) pentru X11.

> **Recomandat:** un runtime JavaScript în `PATH` (**deno**, **node** sau **bun**). YouTube cere rezolvarea
> unor provocări JS; yt-dlp funcționează și fără, dar unele formate pot lipsi. Nocturne îi spune automat
> lui yt-dlp să folosească ce găsește (`js_runtimes`), iar scripturile EJS vin cu `yt-dlp-ejs`.

Opțiuni: `--minimized` (pornește în tray), orice link YouTube ca argument (este adăugat la descărcări),
`nocturne://play_pause|next|previous|open_add_link|show`. `NOCTURNE_DEBUG=1` = jurnal detaliat.

---

## Build Windows (.exe + portabil)

Necesită: Python 3.12, [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`).

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

Rezultat în `dist\`:

| Fișier | Ce este |
|---|---|
| `NocturneSetup-1.0.0.exe` | installer (per utilizator, fără drepturi de admin): meniu Start, scurtătură desktop opțională, „Pornește cu Windows” opțional, dezinstalare, protocol `nocturne://` |
| `Nocturne-1.0.0-windows-portable.zip` | build-ul `--onedir`, rulează fără instalare |
| `Nocturne\` | folderul PyInstaller |

Această ediție are widgetul desktop și mini-playerul, **fără** widgetul Win+W (vezi MSIX mai jos).

---

## Ediția completă Windows (MSIX + widget Win+W)

Panoul Widgets din Windows 11 acceptă doar furnizori COM **împachetați**, așa că partea asta nu e Python:
`widget-bridge/` (C# .NET 8, Windows App SDK) implementează `IWidgetProvider` cu șabloane Adaptive Card
(mic / mediu / mare). Nu conține logică de player: comunică cu aplicația Python prin
`\\.\pipe\nocturne` (linii JSON) și, dacă aplicația nu rulează, o pornește prin `nocturne://<comandă>`.
Textele cardurilor vin din câmpul `lang`, deci schimbarea limbii actualizează și cardurile Win+W.

Necesită în plus: [.NET 8 SDK](https://dotnet.microsoft.com/download) (`winget install Microsoft.DotNet.SDK.8`).

```powershell
powershell -ExecutionPolicy Bypass -File packaging\msix\build_msix.ps1
```

Scriptul:

1. construiește aplicația Python (PyInstaller) și puntea C# (`dotnet publish`, self-contained);
2. le pune împreună într-un singur `dist\Nocturne-1.0.0.msix` (`makeappx` din NuGet `Microsoft.Windows.SDK.BuildTools`);
3. creează **o singură dată** un certificat autosemnat gratuit `CN=Nocturne Dev`
   (`packaging\msix\NocturneDev.pfx` / `.cer`, parola `nocturne`) și semnează pachetul;
4. adaugă certificatul în `LocalMachine\TrustedPeople` (**o fereastră UAC**) și instalează pachetul
   împreună cu framework-ul Windows App Runtime de care depinde.

Doar build, fără instalare: `-NoInstall`. Reutilizează un build PyInstaller existent: `-SkipPyInstaller`.

**Adăugarea widgetului în panoul Win+W**

1. Pornește Nocturne o dată (din meniul Start, „Nocturne”).
2. Apasă **Win+W** → butonul **+** („Adaugă widgeturi”) din dreapta sus.
3. Alege **Nocturne** → **Fixează**. Din „⋯” pe widget poți alege dimensiunea **Mică / Medie / Mare**.
4. Mic = copertă + titlu + play/pauză; Mediu = „SE REDĂ ACUM” + anterioara / play-pauză / următoarea;
   Mare = în plus „Adăugate recent” (2 melodii) și butonul „Adaugă link YouTube”, care deschide ecranul de adăugare.

Dacă Nocturne nu apare în listă: verifică faptul că ai Windows 11 cu panoul Widgets activ și că widgeturile de la
terți sunt disponibile în regiunea ta; deloghează-te / reloghează-te o dată după prima instalare.
Jurnalul punții: `%LOCALAPPDATA%\Nocturne\widget-bridge.log` (în containerul pachetului).

Dezinstalare: *Setări → Aplicații → Nocturne → Dezinstalare*. Certificatul se poate șterge din
`certlm.msc → Persoane de încredere → Certificate`.

---

## Build Linux (AppImage)

AppImage-ul trebuie construit pe un **glibc vechi** ca să ruleze pe orice distribuție
(Fedora, Ubuntu, Debian, Arch, openSUSE, Mint…). Cel mai simplu, cu Docker:

```bash
docker run --rm -v "$PWD":/src -w /src ubuntu:22.04 bash packaging/build_linux.sh
```

(`ubuntu:22.04` = glibc 2.35, minimul cerut de PySide6 6.12 — merge pe Ubuntu 22.04+, Debian 12+, Fedora 36+.) Scriptul instalează bibliotecile
Qt necesare, rulează PyInstaller, adaugă `AppRun`, `.desktop`, iconițele și pluginurile Qt **xcb + wayland**
și pluginul multimedia **FFmpeg**, apoi rulează `appimagetool`.

Rezultat: `dist/Nocturne-1.0.0-x86_64.AppImage`

```bash
chmod +x Nocturne-1.0.0-x86_64.AppImage
./Nocturne-1.0.0-x86_64.AppImage
```

**Cerință la rulare:** `libfuse2` (Ubuntu 22.04+: `sudo apt install libfuse2`; Fedora: `fuse-libs`).
Fără FUSE: `./Nocturne-1.0.0-x86_64.AppImage --appimage-extract-and-run`.
La prima pornire, AppImage-ul își înregistrează intrarea în meniu și handler-ul `nocturne://` în `~/.local/share/applications`.

**Flatpak (opțional, local):**

```bash
flatpak install flathub org.kde.Platform//6.8 org.kde.Sdk//6.8
flatpak-builder --user --install --force-clean build/flatpak packaging/flatpak/io.github.nocturne.yml
flatpak run io.github.nocturne
```

**Tray pe GNOME:** GNOME nu are tray fără extensia **AppIndicator and KStatusNotifierItem Support**.
Fără ea, închiderea ferestrei închide aplicația (setarea „Rămâi pornit când fereastra e închisă” schimbă asta;
repornirea lui Nocturne aduce fereastra înapoi). Pe **Wayland**, compozitorul decide poziția ferestrelor,
deci „Mereu deasupra” și poziția widgetului pot fi ignorate; sub X11/XWayland totul merge complet.

---

## Widgeturi Linux (KDE / GNOME)

**KDE Plasma 6** — plasmoid propriu (card mare + „pastilă” în panou), citește datele MPRIS ale lui Nocturne:

```bash
kpackagetool6 -t Plasma/Applet -i packaging/plasmoid/io.github.nocturne.widget
# actualizare: kpackagetool6 -t Plasma/Applet -u packaging/plasmoid/io.github.nocturne.widget
```

sau din aplicație: *Setări → Sistem → Instalează widgetul KDE* (apare doar pe Plasma).
Apoi: clic dreapta pe desktop/panou → *Adaugă widgeturi…* → **Nocturne**.

**GNOME 45+** — GNOME nu are widgeturi pe desktop; controalele apar automat în zona media din
meniul rapid/notificări (prin MPRIS). Opțional, o extensie adaugă un mini-player Nocturne în bara de sus:

```bash
cp -r packaging/gnome-extension/nocturne@nocturne ~/.local/share/gnome-shell/extensions/
gnome-extensions enable nocturne@nocturne     # pe Wayland: delogare/relogare înainte
```

**XFCE, Cinnamon, MATE etc.:** widgetul desktop al aplicației (fereastra fără margini) este widgetul.

---

## Actualizarea yt-dlp

YouTube se schimbă des și versiunile vechi de yt-dlp încetează să funcționeze.
*Setări → yt-dlp* arată versiunea curentă; **Caută actualizări** descarcă ultima versiune oficială
(zipapp-ul `yt-dlp` de pe GitHub, verificat cu `SHA2-256SUMS`) în folderul de date al utilizatorului.
După **Repornește**, Nocturne o folosește în locul celei incluse — funcționează și în build-urile `.exe`/AppImage,
fără reinstalare. Din sursă poți și: `python -m pip install -U "yt-dlp[default]"`.

---

## Traduceri

Fluxul Qt Linguist: toate textele QML sunt în `qsTr()`, cele din Python în `QCoreApplication.translate()`.

```bash
python tools/i18n_tool.py update    # extrage textele → nocturne/i18n/nocturne_{ro,en,ru}.ts
python tools/i18n_tool.py check     # arată ce nu e tradus
python tools/i18n_tool.py release   # compilează .ts → .qm (pyside6-lrelease)
```

Fișierele `.ts` se pot edita și cu Qt Linguist (`pyside6-linguist`). Pluralele folosesc formele Qt:
RO: 1 melodie / 2 melodii / 20 de melodii · RU: 1 песня / 2 песни / 5 песен · EN: 1 song / 2 songs.
Datele, duratele, mărimile și numerele urmează limba aleasă („4,2 MB/s” RO/RU, „4.2 MB/s” EN;
„12 nov.” / „Nov 12” / „12 нояб.”). La schimbarea limbii se instalează noul `QTranslator` și se apelează
`QQmlEngine.retranslate()`, deci se actualizează instantaneu fereastra, tray-ul, widgeturile, notificările,
butoanele din taskbar și cardurile Win+W.

---

## Date, jurnale, depanare

| | Windows | Linux |
|---|---|---|
| Bază de date, setări, coperți | `%APPDATA%\Nocturne` | `~/.local/share/nocturne` |
| Jurnal (rotativ, 5 × 2 MB) | `%APPDATA%\Nocturne\logs\nocturne.log` | `~/.local/share/nocturne/logs/nocturne.log` |
| Muzica | `%USERPROFILE%\Music\Nocturne` | `XDG_MUSIC_DIR/Nocturne` |

*Setări → Despre → Deschide folderul de jurnale.*

- **Descărcările eșuează brusc** → *Setări → yt-dlp → Caută actualizări*, apoi *Reîncearcă* în Descărcări.
- **„Only some players support this container”** în jurnal → avertisment inofensiv al yt-dlp; QtMultimedia (FFmpeg) redă m4a DASH fără probleme.
- **Nu se aude nimic pe Linux** → verifică PulseAudio/PipeWire; AppImage-ul include backend-ul FFmpeg al Qt.
- **Dacă calea profilului Windows conține un apostrof** (ex. `Ion's PC`), puntea C# folosește automat
  `build\nuget` ca folder de pachete NuGet (vezi `widget-bridge/Directory.Build.props`).

---

## Listă de test

1. **Descarcă un playlist**: lipește un link `…playlist?list=…` (sau Ctrl+V oriunde) → apare în *Descărcări* cu
   progres, viteză și bara globală; progresul apare și pe pictograma din taskbar (Windows); la final, notificare
   „Playlist descărcat” și un playlist nou în bara laterală.
2. **Redă**: dublu-clic pe o melodie → rândul devine ambră cu ▶, cardul „SE REDĂ ACUM” și bara de jos se actualizează.
3. **Închide fereastra** → muzica continuă; pictograma din tray are meniu cu Play/Pauză/Următoarea/Ieșire.
4. **Tastele media** de pe tastatură → play/pauză, următoarea, anterioara funcționează cu fereastra ascunsă.
5. **Widgetul media al sistemului**: Windows — flyout-ul de volum / ecranul de blocare arată titlul, artistul,
   coperta și butoanele; Linux — widgetul media GNOME/KDE (MPRIS) arată același lucru și butoanele funcționează.
6. **Butoanele din taskbar** (Windows): treci cu mouse-ul peste pictograma din taskbar → anterioara / play-pauză /
   următoarea; pictograma play↔pauză se schimbă live.
7. **Widget desktop**: *Bara de jos → ⧉ → Arată widgetul desktop* → butoanele merg; trage-l, schimbă dimensiunea din „⋯”,
   „Mereu deasupra”, „Fixează pe desktop”; închide fereastra principală — widgetul rămâne și funcționează.
8. **Win+W** (ediția MSIX) / **plasmoidul KDE**: butoanele anterioara / play-pauză / următoarea controlează playerul;
   „Adaugă link YouTube” (card mare) deschide ecranul de adăugare.
9. **Melodia următoare pornește automat** la finalul celei curente (cu repetare „toate”, coada reîncepe; „una” repetă).
10. **Schimbă limba live**: *Setări → Limbă → English / Русский* (sau din meniul tray) → toată interfața, tray-ul,
    widgeturile, tooltip-urile din taskbar și cardurile Win+W se schimbă instant.
11. **Repornește aplicația** → coada, ultima melodie și poziția sunt restaurate.

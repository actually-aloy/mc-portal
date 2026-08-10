# MC Portal

A tiny Windows utility that opens and closes the Minecraft port in your firewall with one click — visualized as a Nether portal that lights up when the port is open.

![Platform](https://img.shields.io/badge/platform-Windows-0a0414?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-9b3bff?style=flat-square)
![Version](https://img.shields.io/badge/version-1.0-6a1fc9?style=flat-square)
![License](https://img.shields.io/badge/license-source--available-ecd9ff?style=flat-square)

## What it does

Hosting a Minecraft Java server means poking a hole in the Windows Firewall for TCP port 25565, then remembering to close it again when you're done. MC Portal turns that into a single button:

- **Open Portal** — adds an inbound firewall rule for TCP 25565
- **Close Portal** — removes it
- The portal itself doubles as the status indicator: dark and dormant when closed, glowing and animated when the port is open

## Features

- One-click firewall rule management via `netsh advfirewall`
- Custom frameless UI with a live Nether portal indicator
- System tray support — minimize instead of quitting, with a tray menu to show the window, toggle the port, or quit
- Self-elevates for admin rights on launch (required for firewall changes)
- Single-instance lock — launching it twice just focuses the existing warning, it won't spawn duplicates
- Configurable behavior:
  - Open the port automatically on launch (off by default)
  - Close the port automatically on exit (on by default)
  - Minimize to tray instead of closing (on by default)
- Settings are stored in a plain `settings.json` next to the app, no registry writes
- Checks GitHub Releases on launch and shows an in-app banner if a newer version is available

## Getting started

### Requirements

- Windows 10/11
- Python 3.10+

```bash
pip install pywebview pillow pystray
```

### Run from source

```bash
git clone https://github.com/actually-aloy/mc-portal.git
cd mc-portal
python mc_portal.py
```

The app will prompt for admin rights on launch — this is required to add/remove firewall rules.

### Build a standalone .exe

```bash
pyinstaller --onefile --noconsole --icon=icon.ico mc_portal.py
```

Keep `icon.ico` in the same folder as the built `.exe` — it's loaded at runtime for the tray icon, not just baked into the executable.

## Settings

| Setting | Default | Description |
|---|---|---|
| Open port on launch | Off | Opens TCP 25565 automatically when the app starts |
| Close port on exit | On | Closes TCP 25565 when you fully quit (via the tray menu or with "minimize to tray" off) |
| Minimize to tray | On | The close button hides the window instead of quitting the app |

## Notes

- Targets **Minecraft Java Edition** (TCP 25565). Bedrock Edition uses UDP 19132 and isn't covered.
- Requires administrator privileges, since firewall rules can't be managed otherwise.
- You're still responsible for forwarding the port on your router if you want players outside your LAN to connect — this app only manages the local Windows Firewall rule.

## License

Source-available, not open source in the OSI sense — see [LICENSE.txt](LICENSE.txt). You're welcome to read the code, run releases, and submit pull requests. Redistributing, repackaging, or using the code in another project isn't permitted.

## Contact

- Telegram: [@actually_aloy](https://t.me/actually_aloy)
- GitHub: [actually-aloy](https://github.com/actually-aloy)
- Website: [actually-aloy.github.io/site](https://actually-aloy.github.io/site)

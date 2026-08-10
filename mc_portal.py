import os
import sys
import json
import ctypes
import threading
import webbrowser
import subprocess
import urllib.request

import webview
from PIL import Image
import pystray

APP_NAME = "MC Portal"
APP_VERSION = "1.0"
PORT = 25565
RULE_NAME = "MC Portal (Minecraft Server)"
UPDATE_REPO = "actually-aloy/mc-portal"

GITHUB_URL = "https://github.com/actually-aloy"
WEBSITE_URL = "https://actually-aloy.github.io/site"
TELEGRAM_URL = "https://t.me/actually_aloy"

DEFAULT_SETTINGS = {
    "open_on_launch": False,
    "close_on_exit": True,
    "minimize_to_tray": True,
}

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
MUTEX_NAME = "Global\\MCPortal_9F2A61"
ERROR_ALREADY_EXISTS = 183

window = None
tray_icon = None


def acquire_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.user32.MessageBoxW(0, "MC Portal is already running.", "MC Portal", 0x40)
        sys.exit(0)
    return mutex


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(data):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def firewall_rule_exists():
    result = subprocess.run(
        ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return "No rules match the specified criteria" not in result.stdout


def open_port():
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "add", "rule",
         f"name={RULE_NAME}", "dir=in", "action=allow", "protocol=TCP", f"localport={PORT}"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )


def close_port():
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME}"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )


def is_newer_version(remote, local):
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return remote != local


def check_for_update():
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest",
            headers={"User-Agent": "MC-Portal-Update-Check"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.load(resp)
        tag = str(data.get("tag_name", "")).lstrip("vV")
        url = data.get("html_url") or f"https://github.com/{UPDATE_REPO}/releases/latest"
        if tag and is_newer_version(tag, APP_VERSION):
            return {"version": tag, "url": url}
    except Exception:
        pass
    return None


def update_check_worker():
    info = check_for_update()
    if not info:
        return
    for _ in range(10):
        try:
            window.evaluate_js(f"window.showUpdateBanner({json.dumps(info)})")
            return
        except Exception:
            threading.Event().wait(1)


class Api:
    def __init__(self):
        self.settings = load_settings()

    def get_state(self):
        return {"open": firewall_rule_exists(), "port": PORT}

    def toggle(self):
        if firewall_rule_exists():
            close_port()
        else:
            open_port()
        refresh_tray_menu()
        return {"open": firewall_rule_exists(), "port": PORT}

    def get_settings(self):
        return self.settings

    def set_setting(self, key, value):
        if key in DEFAULT_SETTINGS:
            self.settings[key] = value
            save_settings(self.settings)
        return self.settings

    def minimize_window(self):
        window.minimize()

    def request_close(self):
        if self.settings.get("minimize_to_tray"):
            window.hide()
        else:
            if self.settings.get("close_on_exit"):
                close_port()
            if tray_icon:
                tray_icon.stop()
            try:
                window.destroy()
            except Exception:
                pass
            os._exit(0)

    def open_link(self, url):
        if url:
            webbrowser.open(url)


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --bg: #050208;
    --obsidian: #0a0414;
    --obsidian-line: #1c0d34;
    --accent: #9b3bff;
    --accent-soft: #6a1fc9;
    --core: #ecd9ff;
    --text: #d8cfe6;
    --text-dim: #8a7aa3;
    --card: rgba(20, 10, 34, 0.55);
    --card-border: rgba(155, 59, 255, 0.18);
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; height: 100%; width: 100%;
    background: radial-gradient(ellipse at 50% 30%, #150a24, var(--bg) 70%);
    overflow: hidden;
    font-family: 'Segoe UI', system-ui, sans-serif; color: var(--text);
    display: flex; flex-direction: column; align-items: center;
    -webkit-user-select: none; user-select: none;
    border: 1px solid rgba(155,59,255,0.16);
  }
  #titlebar {
    width: 100%; height: 38px; flex-shrink: 0; display: flex;
    align-items: center; gap: 9px; padding: 0 8px 0 14px;
    background: #0a0414;
  }
  #dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #4a3a5c; box-shadow: 0 0 0 rgba(155,59,255,0);
    transition: all 0.6s ease;
  }
  #dot.on { background: var(--accent); box-shadow: 0 0 10px 2px rgba(155,59,255,0.8); }
  #app-title {
    font-size: 12px; font-weight: 600; letter-spacing: 2.5px;
    text-transform: uppercase; color: #b9a8d6;
  }
  #app-version {
    font-size: 9px; color: #4f4463; letter-spacing: 1px;
  }
  #update-banner {
    display: none; align-items: center; justify-content: space-between;
    gap: 10px; margin: 10px 20px 0; padding: 8px 12px;
    background: rgba(155,59,255,0.12); border: 1px solid var(--card-border);
    border-radius: 10px; font-size: 11.5px; color: var(--text); flex-shrink: 0;
  }
  #update-banner.show { display: flex; }
  #update-btn {
    border: none; border-radius: 6px; padding: 5px 12px; font-size: 11px;
    font-weight: 600; letter-spacing: 0.5px; cursor: pointer;
    background: var(--accent); color: #fff;
  }
  #update-btn:hover { background: var(--accent-soft); }
  #title-spacer { flex: 1; }
  .win-btn {
    width: 30px; height: 26px; border: none; background: transparent;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; border-radius: 5px; color: #a894c4;
  }
  .win-btn:hover { background: rgba(155,59,255,0.15); color: #fff; }
  #close-btn:hover { background: #c22c4a; color: #fff; }
  .win-btn svg { width: 11px; height: 11px; }
  #portal-wrap {
    flex: 1; width: 100%; display: flex;
    align-items: center; justify-content: center;
    padding: 8px 30px; min-height: 0;
  }
  #frame {
    width: min(56%, 340px); height: 82%; max-height: 380px;
    position: relative; border-radius: 14px;
    background:
      linear-gradient(var(--obsidian), var(--obsidian)) padding-box,
      repeating-linear-gradient(0deg, var(--obsidian-line) 0 16px, var(--obsidian) 16px 18px),
      repeating-linear-gradient(90deg, var(--obsidian-line) 0 26px, var(--obsidian) 26px 28px);
    box-shadow: inset 0 0 0 1px rgba(155,59,255,0.08), 0 0 0 rgba(155,59,255,0);
    transition: box-shadow 1s ease;
  }
  #frame.on {
    box-shadow: inset 0 0 0 1px rgba(200,150,255,0.25), 0 0 55px 6px rgba(139,50,255,0.35);
  }
  #surface {
    position: absolute; inset: 26px; border-radius: 6px;
    background: #030103; overflow: hidden;
    transition: background 1.2s ease;
  }
  #frame.on #surface {
    background:
      radial-gradient(ellipse at 32% 35%, rgba(220,160,255,0.6), transparent 55%),
      radial-gradient(ellipse at 68% 65%, rgba(150,60,230,0.65), transparent 55%),
      linear-gradient(150deg, #4b0f8c, #150226 75%);
    animation: swirl 7s ease-in-out infinite alternate, flicker 2.4s infinite;
  }
  @keyframes swirl {
    0% { background-position: 0% 0%, 100% 100%, 0 0; filter: hue-rotate(0deg) saturate(1); }
    100% { background-position: 35% 15%, 65% 85%, 0 0; filter: hue-rotate(20deg) saturate(1.15); }
  }
  @keyframes flicker {
    0%, 100% { opacity: 1; } 46% { opacity: 0.93; } 50% { opacity: 0.82; } 54% { opacity: 0.96; }
  }
  .particle {
    position: absolute; bottom: -8px; width: 3px; height: 3px;
    background: #dbb2ff; border-radius: 50%;
    box-shadow: 0 0 6px 2px rgba(200,140,255,0.9);
    animation: rise linear infinite;
  }
  @keyframes rise {
    0% { transform: translateY(0) translateX(0); opacity: 0; }
    12% { opacity: 1; }
    100% { transform: translateY(-90%) translateX(var(--dx)); opacity: 0; }
  }
  #status-row {
    display: flex; flex-direction: column; align-items: center;
    gap: 2px; margin-top: 2px; flex-shrink: 0;
  }
  #status {
    font-size: 12px; letter-spacing: 2px; text-transform: uppercase;
    color: var(--text-dim);
  }
  #status b { color: var(--core); font-weight: 600; }
  #port-label { font-size: 10px; color: #5f5372; letter-spacing: 1px; }
  #controls {
    width: 100%; padding: 16px 24px 8px; display: flex;
    flex-direction: column; align-items: center; gap: 14px; flex-shrink: 0;
  }
  #toggle-btn {
    padding: 12px 40px; font-size: 13px; font-weight: 700;
    border: 1px solid var(--card-border); border-radius: 30px; cursor: pointer;
    background: linear-gradient(180deg, #2a1147, #190a2c); color: var(--core);
    letter-spacing: 2px; text-transform: uppercase;
    transition: all 0.25s ease;
  }
  #toggle-btn:hover { border-color: rgba(200,150,255,0.5); transform: translateY(-1px); }
  #toggle-btn:active { transform: translateY(0); }
  #toggle-btn.on {
    background: linear-gradient(180deg, var(--accent), var(--accent-soft));
    box-shadow: 0 0 22px rgba(155,59,255,0.55);
    color: #fff;
  }
  #toggle-btn:disabled { opacity: 0.5; cursor: default; }
  #settings-card {
    width: 100%; max-width: 360px; background: var(--card);
    border: 1px solid var(--card-border); border-radius: 12px;
    overflow: hidden;
  }
  #settings-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 16px; cursor: pointer;
  }
  #settings-header span {
    font-size: 10px; letter-spacing: 2px; text-transform: uppercase;
    color: var(--text-dim);
  }
  #chevron { transition: transform 0.25s ease; color: var(--text-dim); }
  #settings-card.open #chevron { transform: rotate(180deg); }
  #settings-body {
    max-height: 0; opacity: 0; overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.25s ease;
    padding: 0 16px;
  }
  #settings-card.open #settings-body {
    max-height: 200px; opacity: 1; padding: 0 16px 10px;
  }
  .setting-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 7px 0;
  }
  .setting-row span { font-size: 12.5px; color: var(--text); }
  .switch { position: relative; width: 36px; height: 20px; flex-shrink: 0; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider {
    position: absolute; inset: 0; background: #2b1f3d; border-radius: 20px;
    cursor: pointer; transition: background 0.25s ease;
  }
  .slider::before {
    content: ""; position: absolute; width: 14px; height: 14px; left: 3px; top: 3px;
    background: #cfc2e0; border-radius: 50%; transition: transform 0.25s ease, background 0.25s ease;
  }
  input:checked + .slider { background: var(--accent-soft); }
  input:checked + .slider::before { transform: translateX(16px); background: #fff; }
  #footer {
    width: 100%; flex-shrink: 0; display: flex; align-items: center;
    justify-content: center; gap: 22px; padding: 12px 0 16px;
  }
  .social-link {
    width: 30px; height: 30px; border-radius: 8px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-dim); transition: all 0.2s ease;
  }
  .social-link:hover { color: var(--core); background: rgba(155,59,255,0.12); }
  .social-link svg { width: 16px; height: 16px; }
</style>
</head>
<body>
  <div id="titlebar" class="pywebview-drag-region">
    <div id="dot"></div>
    <div id="app-title">MC Portal</div>
    <div id="app-version">__APP_VERSION__</div>
    <div id="title-spacer"></div>
    <button class="win-btn" id="min-btn">
      <svg viewBox="0 0 10 10"><rect x="0" y="4.5" width="10" height="1.2" fill="currentColor"/></svg>
    </button>
    <button class="win-btn" id="close-btn">
      <svg viewBox="0 0 10 10"><line x1="0" y1="0" x2="10" y2="10" stroke="currentColor" stroke-width="1.2"/><line x1="10" y1="0" x2="0" y2="10" stroke="currentColor" stroke-width="1.2"/></svg>
    </button>
  </div>
  <div id="update-banner">
    <span id="update-text"></span>
    <button id="update-btn">Get it</button>
  </div>
  <div id="portal-wrap">
    <div id="frame">
      <div id="surface"></div>
    </div>
  </div>
  <div id="status-row">
    <div id="status">Portal <b id="state-word">Closed</b></div>
    <div id="port-label">TCP PORT 25565</div>
  </div>
  <div id="controls">
    <button id="toggle-btn">Open Portal</button>
    <div id="settings-card">
      <div id="settings-header">
        <span>Settings</span>
        <svg id="chevron" viewBox="0 0 12 8" width="12" height="8">
          <path d="M1 1L6 6L11 1" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div id="settings-body">
        <div class="setting-row">
          <span>Open port on launch</span>
          <label class="switch">
            <input type="checkbox" id="open-on-launch">
            <span class="slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <span>Close port on exit</span>
          <label class="switch">
            <input type="checkbox" id="close-on-exit">
            <span class="slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <span>Minimize to tray</span>
          <label class="switch">
            <input type="checkbox" id="minimize-to-tray">
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>
  </div>
  <div id="footer">
    <div class="social-link" id="link-telegram" title="Telegram">
      <svg viewBox="0 0 24 24" fill="none"><path d="M21 3L2 11.5l6 2m13-10.5l-4 17-7-6m11-11L8 13.5m0 0l-.5 5.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </div>
    <div class="social-link" id="link-website" title="Website">
      <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9s1.3-6.4 3.8-9z" stroke="currentColor" stroke-width="1.6"/></svg>
    </div>
    <div class="social-link" id="link-github" title="GitHub">
      <svg viewBox="0 0 24 24" fill="none"><circle cx="6" cy="8" r="2.6" stroke="currentColor" stroke-width="1.6"/><circle cx="18" cy="8" r="2.6" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="17" r="2.6" stroke="currentColor" stroke-width="1.6"/><path d="M8.2 9.6L10.4 15M15.8 9.6L13.6 15M8.6 8H15.4" stroke="currentColor" stroke-width="1.6"/></svg>
    </div>
  </div>

<script>
const frame = document.getElementById('frame');
const dot = document.getElementById('dot');
const btn = document.getElementById('toggle-btn');
const stateWord = document.getElementById('state-word');
const openOnLaunch = document.getElementById('open-on-launch');
const closeOnExit = document.getElementById('close-on-exit');
const minimizeToTray = document.getElementById('minimize-to-tray');
const settingsCard = document.getElementById('settings-card');
const settingsHeader = document.getElementById('settings-header');
const minBtn = document.getElementById('min-btn');
const closeBtn = document.getElementById('close-btn');
let particleTimer = null;

function spawnParticles() {
  if (particleTimer) return;
  particleTimer = setInterval(() => {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.left = (18 + Math.random() * 64) + '%';
    p.style.setProperty('--dx', (Math.random() * 30 - 15) + 'px');
    p.style.animationDuration = (2 + Math.random() * 2) + 's';
    frame.appendChild(p);
    setTimeout(() => p.remove(), 4200);
  }, 260);
}

function stopParticles() {
  clearInterval(particleTimer);
  particleTimer = null;
}

function applyState(state) {
  if (state.open) {
    frame.classList.add('on');
    dot.classList.add('on');
    btn.classList.add('on');
    btn.textContent = 'Close Portal';
    stateWord.textContent = 'Open';
    spawnParticles();
  } else {
    frame.classList.remove('on');
    dot.classList.remove('on');
    btn.classList.remove('on');
    btn.textContent = 'Open Portal';
    stateWord.textContent = 'Closed';
    stopParticles();
  }
}

async function refreshState() {
  const state = await window.pywebview.api.get_state();
  applyState(state);
}
window.refreshState = refreshState;

btn.addEventListener('click', async () => {
  btn.disabled = true;
  const state = await window.pywebview.api.toggle();
  applyState(state);
  btn.disabled = false;
});

openOnLaunch.addEventListener('change', () => {
  window.pywebview.api.set_setting('open_on_launch', openOnLaunch.checked);
});
closeOnExit.addEventListener('change', () => {
  window.pywebview.api.set_setting('close_on_exit', closeOnExit.checked);
});
minimizeToTray.addEventListener('change', () => {
  window.pywebview.api.set_setting('minimize_to_tray', minimizeToTray.checked);
});

settingsHeader.addEventListener('click', () => {
  settingsCard.classList.toggle('open');
});

[minBtn, closeBtn, settingsHeader].forEach(el => {
  el.addEventListener('mousedown', e => e.stopPropagation());
});

minBtn.addEventListener('click', () => window.pywebview.api.minimize_window());
closeBtn.addEventListener('click', () => window.pywebview.api.request_close());

document.getElementById('link-telegram').addEventListener('click', () => {
  window.pywebview.api.open_link('__TELEGRAM_URL__');
});
document.getElementById('link-website').addEventListener('click', () => {
  window.pywebview.api.open_link('__WEBSITE_URL__');
});
document.getElementById('link-github').addEventListener('click', () => {
  window.pywebview.api.open_link('__GITHUB_URL__');
});

window.addEventListener('pywebviewready', async () => {
  await refreshState();
  const settings = await window.pywebview.api.get_settings();
  openOnLaunch.checked = settings.open_on_launch;
  closeOnExit.checked = settings.close_on_exit;
  minimizeToTray.checked = settings.minimize_to_tray;
});

window.showUpdateBanner = function(info) {
  document.getElementById('update-text').textContent = 'Update available — v' + info.version;
  document.getElementById('update-btn').onclick = () => window.pywebview.api.open_link(info.url);
  document.getElementById('update-banner').classList.add('show');
};
</script>
</body>
</html>
"""

HTML = (
    HTML.replace("__TELEGRAM_URL__", TELEGRAM_URL)
    .replace("__WEBSITE_URL__", WEBSITE_URL)
    .replace("__GITHUB_URL__", GITHUB_URL)
    .replace("__APP_VERSION__", "v" + APP_VERSION)
)


def show_window(icon=None, item=None):
    window.show()
    window.evaluate_js("window.refreshState && window.refreshState()")


def toggle_from_tray(icon=None, item=None):
    if firewall_rule_exists():
        close_port()
    else:
        open_port()
    refresh_tray_menu()
    try:
        window.evaluate_js("window.refreshState && window.refreshState()")
    except Exception:
        pass


def quit_app(icon=None, item=None, api=None):
    if api and api.settings.get("close_on_exit"):
        close_port()
    if tray_icon:
        tray_icon.stop()
    try:
        window.destroy()
    except Exception:
        pass
    os._exit(0)


def build_menu(api):
    state_text = "Close Port" if firewall_rule_exists() else "Open Port"
    return pystray.Menu(
        pystray.MenuItem("Show MC Portal", show_window, default=True),
        pystray.MenuItem(state_text, toggle_from_tray),
        pystray.MenuItem("Quit", lambda icon, item: quit_app(icon, item, api)),
    )


def refresh_tray_menu():
    if tray_icon:
        tray_icon.menu = build_menu(tray_icon.api_ref)
        tray_icon.update_menu()


def start_tray(api):
    global tray_icon
    image = Image.open(ICON_PATH) if os.path.exists(ICON_PATH) else Image.new("RGBA", (32, 32), (155, 59, 255, 255))
    tray_icon = pystray.Icon(APP_NAME, image, APP_NAME, menu=build_menu(api))
    tray_icon.api_ref = api
    tray_icon.run()


def main():
    if not is_admin():
        run_as_admin()
        return

    acquire_single_instance()

    global window
    api = Api()

    if api.settings.get("open_on_launch"):
        open_port()

    window = webview.create_window(
        f"{APP_NAME} v{APP_VERSION}", html=HTML, js_api=api,
        width=440, height=700, resizable=True, background_color="#050208",
        frameless=True, easy_drag=False
    )

    def on_closing():
        if api.settings.get("minimize_to_tray"):
            window.hide()
            return False
        if api.settings.get("close_on_exit"):
            close_port()
        if tray_icon:
            tray_icon.stop()
        return True

    window.events.closing += on_closing

    threading.Thread(target=start_tray, args=(api,), daemon=True).start()
    threading.Thread(target=update_check_worker, daemon=True).start()

    webview.start()
    os._exit(0)


if __name__ == "__main__":
    main()

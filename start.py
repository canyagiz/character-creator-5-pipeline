"""
start.py — CC5'i baslatir, loader.py'yi yukler, RAM watchdog olarak devam eder.
Kullanim:  python start.py
Gereksinim: pip install pywin32 psutil
"""

import os, sys, time, subprocess, ctypes
import psutil
import win32gui, win32con, win32api
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "props"))
from local_config import (CC5_EXE, NODE_ID,
                          CANCEL_POPUP_XY, SCRIPT_MENU_XY, LOAD_PYTHON_XY)

# Toplam RAM'in %80'i, minimum 8 GB
MAX_CC5_RAM_GB = max(8.0, psutil.virtual_memory().total / 1024**3 * 0.80)

LOADER_SCRIPT    = str(Path(__file__).parent / "props" / "loader.py")
META_DIR         = Path(__file__).parent / "renders" / "meta"
CHECK_INTERVAL   = 30
CC5_LOAD_WAIT    = 120
DIALOG_TIMEOUT   = 20
IDLE_TIMEOUT_MIN = 5    # meta'da bu kadar dakika yeni dosya yoksa yeniden baslatir

def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)

# ── Yardimci fonksiyonlar ─────────────────────────────────────────────────────
def get_cc5_ram_gb():
    total = 0.0
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            if p.info["name"] == "CharacterCreator.exe":
                total += p.info["memory_info"].rss / 1024**3
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total

def kill_cc5():
    log("CC5 kapatiliyor...")
    subprocess.run(["taskkill", "/f", "/im", "CharacterCreator.exe"], capture_output=True)
    for _ in range(15):
        if get_cc5_ram_gb() == 0:
            log("CC5 kapandi.")
            return
        time.sleep(1)

def find_cc5_hwnd():
    result = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and "Character Creator 5" in win32gui.GetWindowText(hwnd):
            result.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return result[0] if result else None

def _force_foreground(hwnd):
    fg = win32gui.GetForegroundWindow()
    if fg == hwnd:
        return
    try:
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(fg, None)
        my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        ctypes.windll.user32.AttachThreadInput(my_tid, fg_tid, True)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.AttachThreadInput(my_tid, fg_tid, False)
    except Exception:
        win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.3)

def _mouse_click(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.1)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.2)

def dismiss_project_popup():
    """CC5 yeniden acilirken cikan proje popup'ini kapatir."""
    log(f"Proje popup kapatiliyor: {CANCEL_POPUP_XY}")
    _mouse_click(*CANCEL_POPUP_XY)
    time.sleep(2.5)

def trigger_load_python(hwnd):
    """Script > Load Python'i local_config koordinatlariyla tıklar."""
    _force_foreground(hwnd)
    time.sleep(0.3)
    log(f"Script tiklanıyor: {SCRIPT_MENU_XY}")
    _mouse_click(*SCRIPT_MENU_XY)
    time.sleep(2.5)
    log(f"Load Python tiklanıyor: {LOAD_PYTHON_XY}")
    _mouse_click(*LOAD_PYTHON_XY)
    return True

def is_rendering_active():
    """Meta dizininde son IDLE_TIMEOUT_MIN dakikada yeni dosya varsa True döner."""
    if not META_DIR.exists():
        return True  # dizin yoksa henuz baslamadi, mudahale etme
    cutoff = time.time() - IDLE_TIMEOUT_MIN * 60
    return any(p.stat().st_mtime > cutoff for p in META_DIR.iterdir() if p.is_file())

def fill_open_dialog():
    log("Dosya diyalogu bekleniyor...")
    deadline = time.time() + DIALOG_TIMEOUT
    while time.time() < deadline:
        for title in ("Aç", "Open", "Ac"):
            dlg = win32gui.FindWindow("#32770", title)
            if dlg:
                log(f"Diyalog bulundu ('{title}'), path yaziliyor...")
                cb_ex = win32gui.FindWindowEx(dlg, 0, "ComboBoxEx32", None)
                cb    = win32gui.FindWindowEx(cb_ex, 0, "ComboBox", None) if cb_ex else 0
                edit  = win32gui.FindWindowEx(cb, 0, "Edit", None) if cb else 0
                if not edit:
                    edit = win32gui.FindWindowEx(dlg, 0, "Edit", None)
                if edit:
                    win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, LOADER_SCRIPT)
                    time.sleep(0.3)
                    win32api.PostMessage(edit, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                    win32api.PostMessage(edit, win32con.WM_KEYUP,   win32con.VK_RETURN, 0)
                    log("loader.py yuklendi — batch_export basliyor.")
                    return True
        time.sleep(0.5)
    log("HATA: Diyalog bulunamadi.")
    return False

def launch_and_load():
    """CC5'i ac, yuklensin bekle, loader.py'yi tetikle."""
    log(f"CC5 baslatiliyor: {CC5_EXE}")
    subprocess.Popen([CC5_EXE])
    log(f"CC5 yukleniyor, {CC5_LOAD_WAIT}s bekleniyor...")
    time.sleep(CC5_LOAD_WAIT)

    hwnd = find_cc5_hwnd()
    if not hwnd:
        log("HATA: CC5 penceresi bulunamadi.")
        return False

    log(f"CC5 penceresi bulundu (hwnd={hwnd})")
    dismiss_project_popup()
    if trigger_load_python(hwnd):
        time.sleep(1)
        fill_open_dialog()
        return True
    return False

# ── Baslangic ─────────────────────────────────────────────────────────────────
log(f"=== START.PY === Node={NODE_ID}  MAX_RAM={MAX_CC5_RAM_GB:.1f}GB")
launch_and_load()

# ── Watchdog dongusu ──────────────────────────────────────────────────────────
log("Watchdog dongusu basliyor...")
while True:
    time.sleep(CHECK_INTERVAL)
    ram = get_cc5_ram_gb()

    if ram == 0:
        log("CC5 calısmiyor — yeniden baslatiliyor")
        time.sleep(5)
        launch_and_load()
        continue

    log(f"CC5 RAM: {ram:.1f} / {MAX_CC5_RAM_GB:.1f} GB")

    if ram >= MAX_CC5_RAM_GB:
        log(f"ESIK ASILDI ({ram:.1f} >= {MAX_CC5_RAM_GB:.1f} GB) — yeniden baslatiliyor")
        kill_cc5()
        time.sleep(5)
        launch_and_load()
        continue

    if not is_rendering_active():
        log(f"IDLE: Meta dizininde {IDLE_TIMEOUT_MIN} dk'dir yeni dosya yok — yeniden baslatiliyor")
        kill_cc5()
        time.sleep(5)
        launch_and_load()

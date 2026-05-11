"""
CC5'in hangi komut satiri argümanlarini kabul ettigini test eder.
Sistem Python'u ile calistir (CC5 kapali olmali).
"""

import subprocess
import time
import sys
import psutil
from pathlib import Path

CC5_EXE     = r"C:\Program Files\Reallusion\Character Creator 5\Bin64\CharacterCreator.exe"
LOADER      = r"C:\Users\HP\character-creator-5-pipeline\props\loader.py"
WAIT        = 20   # CC5'in yuklenmesi icin bekleme (saniye)

def kill_cc5():
    subprocess.run(["taskkill", "/f", "/im", "CharacterCreator.exe"], capture_output=True)
    time.sleep(3)

def cc5_running():
    return any(p.info["name"] == "CharacterCreator.exe"
               for p in psutil.process_iter(["name"]))

def test(label, args):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"CMD : {[CC5_EXE] + args}")
    print(f"{'='*60}")
    kill_cc5()
    time.sleep(2)

    proc = subprocess.Popen(
        [CC5_EXE] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print(f"PID: {proc.pid} — {WAIT}s bekleniyor...")
    time.sleep(WAIT)

    # stdout / stderr yakala (non-blocking)
    try:
        stdout, stderr = proc.communicate(timeout=2)
        print(f"stdout: {stdout.decode(errors='replace')[:500] or '(bos)'}")
        print(f"stderr: {stderr.decode(errors='replace')[:500] or '(bos)'}")
        print(f"returncode: {proc.returncode}")
    except subprocess.TimeoutExpired:
        print("Proses hala calisiyor (GUI uygulamasi — beklenen durum)")

    running = cc5_running()
    print(f"CC5 calisiyor: {running}")
    kill_cc5()
    time.sleep(3)

# Arguman varyantlarini test et
test("--help",           ["--help"])
test("-help",            ["-help"])
test("-script",          ["-script", LOADER])
test("--script",         ["--script", LOADER])
test("-run",             ["-run", LOADER])
test("-python",          ["-python", LOADER])
test("-execute",         ["-execute", LOADER])
test("-autorun",         ["-autorun", LOADER])
test("/script",          ["/script", LOADER])

print("\nTUM TESTLER TAMAMLANDI")

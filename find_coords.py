"""
CC5 menu koordinatlarini bul.
Kullanim:
  1) CC5 acik olmali
  2) python find_coords.py
  3) Her geri sayimda fareyi istenen konuma getir — otomatik olcum alir
"""

import ctypes, time

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_cursor():
    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y

def countdown_capture(label, seconds=5):
    print(f"\n>>> '{label}' ustune git — {seconds} saniye var:")
    for i in range(seconds, 0, -1):
        print(f"    {i}...", end="\r", flush=True)
        time.sleep(1)
    x, y = get_cursor()
    print(f"    ALINDI: {label} = ({x}, {y})          ")
    return x, y

print("=" * 50)
print("CC5 Menu Koordinat Bulucu")
print("=" * 50)

script_x, script_y = countdown_capture("Script menu cubugu yazisi")

print("\nSimdi Script menuye tiklayin (Load Python gorunur olmali).")
load_py_x, load_py_y = countdown_capture("Load Python (acik menude)", seconds=8)

print("\n" + "=" * 50)
print("Sonuclar:")
print(f"  Script menu:  ({script_x}, {script_y})")
print(f"  Load Python:  ({load_py_x}, {load_py_y})")
print()
print("start.py icin:")
print(f"  script_cx = {script_x}")
print(f"  lp_x, lp_y = {load_py_x}, {load_py_y}")
print("=" * 50)

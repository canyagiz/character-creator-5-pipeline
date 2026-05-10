"""
monitor_resources.py — Surekli VRAM / RAM / CPU kullanim logu

Kullanim:
  python monitor_resources.py            # 5 sn aralikli, logs/resource/monitor/<tarih>.log
  python monitor_resources.py --interval 10
  python monitor_resources.py --vram-warn 6000

Ctrl+C ile durdurulur.
6500 MB uzerindeki VRAM okumalar ayrica logs/resource/monitor/vram_spikes.log'a yazilir.
"""

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

import psutil

_DEFAULT_LOG = str(
    Path(__file__).parent / "logs" / "resource" / "monitor" /
    (datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log")
)

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--interval",  type=int, default=10,
                    help="Ornekleme araligi saniye (default 10)")
parser.add_argument("--vram-warn", type=int, default=6500,
                    help="Bu MB uzerinde VRAM uyarisi (default 6500)")
parser.add_argument("--log", type=str, default=_DEFAULT_LOG)
args = parser.parse_args()

LOG_PATH = Path(args.log)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SPIKE_LOG = LOG_PATH.parent / "vram_spikes.log"

# ── GPU sorgusu ───────────────────────────────────────────────────────────────
def query_gpu():
    """(vram_used_mb, vram_str, util_str) döndürür."""
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode != 0:
            return 0, "?/?MB", "?%"
        parts = [p.strip() for p in r.stdout.strip().splitlines()[0].split(",")]
        if len(parts) < 3:
            return 0, "?/?MB", "?%"
        util, used, total = parts
        return int(used), f"{used}/{total}MB", f"{util}%"
    except FileNotFoundError:
        return 0, "nvidia-smi yok", "?%"
    except Exception as e:
        return 0, f"hata:{e}", "?%"

# ── Proses RAM sorgusu ────────────────────────────────────────────────────────
_WATCH_PROCS = {"CharacterCreator.exe", "blender.exe", "python.exe"}

def query_proc_mem():
    """İzlenen proseslerin sistem RAM (RSS) kullanimi MB."""
    totals = {}
    for proc in psutil.process_iter(["name", "memory_info"]):
        try:
            n = proc.info["name"]
            if n in _WATCH_PROCS:
                totals[n] = totals.get(n, 0.0) + proc.info["memory_info"].rss / 1024 / 1024
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return "  ".join(f"{k}={v:.0f}MB" for k, v in sorted(totals.items())) or "-"

# ── Ornekleme ─────────────────────────────────────────────────────────────────
def sample():
    ts                    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu                   = psutil.cpu_percent(interval=None)
    ram                   = psutil.virtual_memory()
    vram_mb, vram_s, util = query_gpu()
    procs                 = query_proc_mem()

    line = (
        f"{ts} | "
        f"CPU={cpu:4.1f}%  "
        f"RAM={ram.used/1024**3:.1f}/{ram.total/1024**3:.1f}GB  "
        f"VRAM={vram_s}  GPU={util}  "
        f"|| PROCS(RAM): {procs}"
    )
    is_spike = vram_mb >= args.vram_warn
    if is_spike:
        line = "VRAM! " + line
    return line, is_spike

# ── Log dosyalari ─────────────────────────────────────────────────────────────
log_file   = open(LOG_PATH,  "a", encoding="utf-8", buffering=1)
spike_file = open(SPIKE_LOG, "a", encoding="utf-8", buffering=1)

def log(msg, spike=False):
    print(msg)
    log_file.write(msg + "\n")
    if spike:
        spike_file.write(msg + "\n")

# ── Ana dongu ─────────────────────────────────────────────────────────────────
log(f"\n=== START {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
    f"interval={args.interval}s  vram_warn={args.vram_warn}MB  log={LOG_PATH} ===")

try:
    while True:
        line, is_spike = sample()
        log(line, spike=is_spike)
        time.sleep(args.interval)
except KeyboardInterrupt:
    log(f"=== STOP {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
finally:
    log_file.close()
    spike_file.close()

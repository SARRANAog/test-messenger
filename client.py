# -*- coding: utf-8 -*-
import socket
import threading
import json
import time
import ssl
from datetime import datetime
from typing import Optional, Tuple

# ===== DEFAULT SETTINGS (Fly) =====
DEFAULT_HOST = "wispy-breeze-6674.fly.dev"
DEFAULT_PORT = 443
DEFAULT_TLS = True
# =================================

def send_json(sock: socket.socket, obj: dict) -> None:
    data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(data)

def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")

def receiver(sock: socket.socket) -> None:
    f = sock.makefile("r", encoding="utf-8", newline="\n")
    while True:
        line = f.readline()
        if not line:
            print("\n[!] Connection closed by server.")
            break
        try:
            msg = json.loads(line)
        except Exception:
            print("\n[!] Bad data (not JSON).")
            continue

        t = msg.get("type")
        if t == "msg":
            ts = fmt_ts(int(msg.get("ts", time.time())))
            frm = msg.get("from", "?")
            text = msg.get("text", "")
            print(f"\n[{ts}] {frm}: {text}")
            print("> ", end="", flush=True)
        elif t == "system":
            ts = fmt_ts(int(msg.get("ts", time.time())))
            text = msg.get("text", "")
            print(f"\n[{ts}] {text}")
            print("> ", end="", flush=True)
        elif t == "error":
            print(f"\n[SERVER ERROR] {msg.get('text')}")
            print("> ", end="", flush=True)

def ask(prompt: str, default: Optional[str] = None) -> str:
    if default is not None and default != "":
        s = input(f"{prompt} (Enter = {default}): ").strip()
        return s if s else default
    return input(f"{prompt}: ").strip()

def connect(host: str, port: int, use_tls: bool) -> socket.socket:
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.settimeout(10)
    raw.connect((host, port))
    raw.settimeout(None)

    if not use_tls:
        return raw

    ctx = ssl.create_default_context()
    # SNI is important for fly.dev
    tls_sock = ctx.wrap_socket(raw, server_hostname=host)
    return tls_sock

def try_connect_with_reason(host: str, port: int, use_tls: bool) -> Tuple[Optional[socket.socket], Optional[str]]:
    try:
        sock = connect(host, port, use_tls)
        return sock, None
    except socket.gaierror:
        return None, "Host not found (DNS)."
    except ConnectionRefusedError:
        return None, "Connection refused (service not listening / port blocked)."
    except TimeoutError:
        return None, "Connection timeout."
    except ssl.SSLError as e:
        return None, "TLS error: " + str(e)
    except Exception as e:
        return None, "Error: " + str(e)

def prompt_connection_settings() -> Tuple[str, int, bool]:
    print("\n--- Connection settings ---")
    host = ask("Server host (domain or IP)", DEFAULT_HOST)

    port_str = ask("Port", str(DEFAULT_PORT))
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError
    except Exception:
        print("[!] Invalid port. Using default.")
        port = DEFAULT_PORT

    tls_str = ask("Use TLS? (y/n)", "y" if DEFAULT_TLS else "n").lower()
    use_tls = tls_str.startswith("y")
    return host, port, use_tls

def main() -> None:
    print("=" * 50)
    print(" PY MESSENGER CLIENT ")
    print("=" * 50)

    name = ask("Your name", "User")

    # 1) try default connect silently (only name asked)
    host, port, use_tls = DEFAULT_HOST, DEFAULT_PORT, DEFAULT_TLS
    print(f"\nConnecting to {host}:{port} (TLS={'ON' if use_tls else 'OFF'}) ...")
    sock, reason = try_connect_with_reason(host, port, use_tls)

    # 2) if failed -> ask settings and retry until success or user exits
    while sock is None:
        print(f"[!] Failed: {reason}")
        choice = ask("Retry with custom settings? (y/n)", "y").lower()
        if not choice.startswith("y"):
            return

        host, port, use_tls = prompt_connection_settings()
        print(f"\nConnecting to {host}:{port} (TLS={'ON' if use_tls else 'OFF'}) ...")
        sock, reason = try_connect_with_reason(host, port, use_tls)

    # 3) connected
    try:
        send_json(sock, {"type": "hello", "name": name})

        t = threading.Thread(target=receiver, args=(sock,), daemon=True)
        t.start()

        print("Ready. Type messages.")
        print("Commands: /exit\n")

        while True:
            try:
                text = input("> ")
            except (EOFError, KeyboardInterrupt):
                text = "/exit"

            if text.strip().lower() == "/exit":
                print("Bye.")
                break

            if not text.strip():
                continue

            send_json(sock, {"type": "msg", "text": text})
    finally:
        try:
            sock.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

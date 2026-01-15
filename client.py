# -*- coding: utf-8 -*-
import socket
import threading
import json
import time
import ssl
from datetime import datetime
from typing import Optional

DEFAULT_PORT = 5050

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

def main() -> None:
    print("=" * 50)
    print(" PY MESSENGER CLIENT ")
    print("=" * 50)

    host = ask("Server host (domain or IP)", "127.0.0.1")
    port_str = ask("Port", str(DEFAULT_PORT))
    name = ask("Your name", "User")
    use_tls = ask("Use TLS? (y/n)", "n").lower().startswith("y")

    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError
    except Exception:
        print("[!] Invalid port. Using 5050.")
        port = DEFAULT_PORT

    print(f"\nConnecting to {host}:{port} as {name} (TLS={'ON' if use_tls else 'OFF'}) ...")

    raw = None
    sock = None

    try:
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(10)
        raw.connect((host, port))
        raw.settimeout(None)

        sock = raw
        if use_tls:
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(raw, server_hostname=host)

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

    except ssl.SSLError as e:
        print(f"[!] TLS error: {e}")
    except ConnectionRefusedError:
        print("[!] Connection refused (server not running / port closed).")
    except socket.gaierror:
        print("[!] Host not found. Check the address.")
    except TimeoutError:
        print("[!] Connection timeout. Server unreachable.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        try:
            if sock is not None:
                sock.close()
        except Exception:
            pass
        try:
            if raw is not None:
                raw.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

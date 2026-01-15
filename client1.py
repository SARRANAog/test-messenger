# client1.py
import socket
import threading
import json
import time
from datetime import datetime

SERVER_HOST = "192.168.1.10"  # <-- ВПИШИ IP ТВОЕГО СЕРВЕРА (твоего ПК)
SERVER_PORT = 5050

USERNAME = "User1"  # <-- поменяй имя

def send_json(sock: socket.socket, obj: dict):
    data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(data)

def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")

def receiver(sock: socket.socket):
    f = sock.makefile("r", encoding="utf-8", newline="\n")
    while True:
        line = f.readline()
        if not line:
            print("\n[!] Соединение закрыто сервером.")
            break
        try:
            msg = json.loads(line)
        except Exception:
            print("\n[!] Получен мусор (не JSON).")
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

def main():
    print(f"Подключение к {SERVER_HOST}:{SERVER_PORT} как {USERNAME}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_HOST, SERVER_PORT))

        send_json(sock, {"type": "hello", "name": USERNAME})

        t = threading.Thread(target=receiver, args=(sock,), daemon=True)
        t.start()

        print("Готово. Пиши сообщения. Команды: /exit")
        while True:
            try:
                text = input("> ")
            except (EOFError, KeyboardInterrupt):
                text = "/exit"

            if text.strip().lower() == "/exit":
                print("Выход...")
                break

            send_json(sock, {"type": "msg", "text": text})

if __name__ == "__main__":
    main()

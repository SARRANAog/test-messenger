# client.py
import socket
import threading
import json
import time
from datetime import datetime

DEFAULT_PORT = 5050

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

def ask(prompt: str, default: str | None = None) -> str:
    if default is not None and default != "":
        s = input(f"{prompt} (Enter = {default}): ").strip()
        return s if s else default
    return input(f"{prompt}: ").strip()

def main():
    print("=" * 50)
    print(" PY MESSENGER CLIENT ")
    print("=" * 50)
    host = ask("Адрес сервера (IP или домен)", "127.0.0.1")
    port_str = ask("Порт", str(DEFAULT_PORT))
    name = ask("Твоё имя", "User")

    # валидация порта
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError
    except Exception:
        print("[!] Неверный порт. Использую 5050.")
        port = DEFAULT_PORT

    print(f"\nПодключаюсь к {host}:{port} как {name} ...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            send_json(sock, {"type": "hello", "name": name})

            t = threading.Thread(target=receiver, args=(sock,), daemon=True)
            t.start()

            print("Готово. Пиши сообщения.")
            print("Команды: /exit\n")

            while True:
                try:
                    text = input("> ")
                except (EOFError, KeyboardInterrupt):
                    text = "/exit"

                if text.strip().lower() == "/exit":
                    print("Выход...")
                    break

                # пустые не отправляем
                if not text.strip():
                    continue

                send_json(sock, {"type": "msg", "text": text})

    except ConnectionRefusedError:
        print("[!] Сервер отказал в соединении (порт закрыт/сервер не запущен).")
    except socket.gaierror:
        print("[!] Не могу найти такой хост/домен. Проверь адрес.")
    except TimeoutError:
        print("[!] Таймаут подключения. Сервер недоступен.")
    except Exception as e:
        print(f"[!] Ошибка: {e}")

if __name__ == "__main__":
    main()

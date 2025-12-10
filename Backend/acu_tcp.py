import socket
import threading
import time

class ACUTcp:
    mode = "tcp"

    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()
        self.host = None
        self.port = None

    def connect(self, host: str, port: int, timeout=5.0):
        self.host = host
        self.port = port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        s.settimeout(timeout)
        s.connect((host, port))

        self.sock = s

    def reconnect(self, timeout=5.0):
        if self.host and self.port:
            self.disconnect()
            time.sleep(0.5)
            self.connect(self.host, self.port, timeout=timeout)

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def is_connected(self):
        return self.sock is not None

    def send_and_read(self, frame, retries=3, timeout=5.0):
        if not self.is_connected():
            raise RuntimeError("TCP not connected")

        raw = frame if isinstance(frame, (bytes, bytearray)) else frame.encode("ascii")

        for attempt in range(retries):
            with self.lock:
                try:
                    self.sock.settimeout(timeout)
                    self.sock.sendall(raw)

                    buff = b""
                    start = time.time()

                    while time.time() - start < timeout:
                        chunk = self.sock.recv(4096)
                        if not chunk:
                            continue
                        buff += chunk

                        # CRLF preferred
                        if b"\r\n" in buff:
                            line, _ = buff.split(b"\r\n", 1)
                            return line.decode("ascii", errors="replace").strip()

                        # fallback LF
                        if b"\n" in buff:
                            line = buff.split(b"\n")[0]
                            return line.decode("ascii", errors="replace").strip()

                except socket.timeout:
                    pass
                except Exception:
                    # try reconnect once
                    try:
                        self.reconnect(timeout=timeout)
                    except Exception:
                        pass

            time.sleep(0.2)

        raise TimeoutError("No TCP response after retries")

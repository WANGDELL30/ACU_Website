import serial
import serial.tools.list_ports
import threading
import time

CRLF = b"\r\n"

def xor_checksum(payload: str) -> str:
    csum = 0
    for b in payload.encode("ascii"):
        csum ^= b
    return f"{csum:02x}"

def build_frame(frame_type: str, frame_code: str, *data_fields: str) -> str:
    parts = [f"${frame_type}", frame_code]
    parts.extend(data_fields)
    payload = ",".join(parts)
    csum = xor_checksum(payload[1:])  # exclude $
    return f"{payload},*{csum}\r\n"

class ACUSerial:
    mode = "serial"

    def __init__(self):
        self.ser = None
        self.lock = threading.Lock()

    @staticmethod
    def list_ports():
        return [{"device": p.device, "description": p.description}
                for p in serial.tools.list_ports.comports()]

    def connect(self, port: str, baudrate=38400, timeout=0.5):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        time.sleep(0.1)

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def send_and_read(self, frame: str, retries=3, timeout=0.5):
        if not self.is_connected():
            raise RuntimeError("Serial not connected")

        raw = frame.encode("ascii")

        for _ in range(retries):
            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.write(raw)
                self.ser.flush()

                start = time.time()
                while time.time() - start < timeout:
                    line = self.ser.readline()
                    if line:
                        return line.decode("ascii", errors="replace").strip()

            time.sleep(0.02)

        raise TimeoutError("No response after retries")

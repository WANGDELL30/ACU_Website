import serial
import time

# ==============================
# KONFIGURASI SERIAL
# ==============================
PORT = "COM7"
BAUD = 38400
ser = None

# ==============================
# Fungsi Checksum
# ==============================
def checksum(data: str) -> str:
    x = 0
    for b in data.encode('ascii'):
        x ^= b
    return f"{x:02X}"

# ==============================
# Kirim + baca respon aman
# ==============================
def kirim(body):
    global ser
    if ser is None or not ser.is_open:
        print("❌ Serial belum terkoneksi! gunakan perintah: connect")
        return

    try:
        chk = checksum(body)
        frame = f"${body}*{chk}\r\n"

        print(f"\n>> Mengirim : {frame.strip()}")
        ser.write(frame.encode('ascii'))
        time.sleep(0.15)

        timeout = time.time() + 2
        while time.time() < timeout:
            if ser.in_waiting:
                resp = ser.readline().decode('ascii', errors='ignore').strip()
                if resp:
                    print("<< Respon :", resp)
            else:
                time.sleep(0.05)

    except Exception as e:
        print("⚠ Error saat kirim:", e)
        print("⚠ Coba disconnect lalu connect ulang")

# ==============================
# CONTROL COMMAND
# ==============================
def move(az, el, pol): kirim(f"cmd,dir,{az},{el},{pol}")
def stow(): kirim("cmd,stow")
def search(): kirim("cmd,search")
def stop(): kirim("cmd,stop")
def reset(): kirim("cmd,reset")

# ==============================
# GET / QUERY
# ==============================
def get_show(): kirim("cmd,get show")
def get_sat(): kirim("cmd,get sat")
def get_ver(): kirim("cmd,get ver")
def get_cfg(): kirim("cmd,get cfg")
def get_status(): kirim("cmd,get status")
def get_custom(p): kirim(f"cmd,get {p}")

# ==============================
# SET SAT PARAMETER
# ==============================
def set_sat(name,a,b,c,d,e,f):
    kirim(f"cmd,sat,{name},{a},{b},{c},{d},{e},{f}")




# ==============================
# MAIN PROGRAM
# ==============================
print("\n=== ACU CONTROLLER READY ===")
print("Port default:", PORT)
print("\nKetik *connect* dulu jika belum tersambung")
print("---------------------------------------------------")
print("[Movement]")
print("  <az> <el> <pol>")
print("  stow | search | stop | reset")
print("\n[Query]")
print("  get show | get sat | get ver | get cfg | get status | get <param>")
print("\n[Satelit]")
print("  set sat <name> <A> <B> <C> <D> <E> <F>")
print("\n[Sistem]")
print("  exit/quit → keluar program")
print("---------------------------------------------------\n")

try:
    while True:
        cmd = input("Command: ").strip()

        if cmd in ["exit","quit"]: break
       

        elif cmd=="stow": stow()
        elif cmd=="search": search()
        elif cmd=="stop": stop()
        elif cmd=="reset": reset()

        elif cmd=="get show": get_show()
        elif cmd=="get sat": get_sat()
        elif cmd=="get ver": get_ver()
        elif cmd=="get cfg": get_cfg()
        elif cmd=="get status": get_status()
        elif cmd.startswith("get "): get_custom(cmd[4:])

        elif cmd.startswith("set sat"):
            try:
                parts = cmd.split()
                name,a,b,c,d,e,f = parts[2:9]
                set_sat(name,a,b,c,d,e,f)
            except:
                print("⚠ Format salah!")

        else:
            try:
                az,el,pol = cmd.split()
                move(az,el,pol)
            except:
                print("⚠ Perintah tidak dikenali!")

finally:
    
    print("\nProgram selesai.\n")
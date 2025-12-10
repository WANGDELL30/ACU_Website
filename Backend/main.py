import asyncio
import traceback
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from acu_driver import acu_serial, build_frame, parse_show
from acu_tcp import ACUTcp

app = FastAPI(title="ACU Web Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tcp_acu = ACUTcp()
acu = acu_serial  # active driver pointer


# =========================================================
# Models
# =========================================================
class ConnectSerialReq(BaseModel):
    port: str
    baudrate: int = 38400
    timeout: float = 0.5


class ConnectTcpReq(BaseModel):
    host: str
    port: int
    timeout: float = 2.0


class SendReq(BaseModel):
    frame_type: str = "cmd"
    frame_code: str
    data: List[str] = []
    retries: int = 3
    timeout: float = 0.5


# ---- Satellite ----
class SatSetReq(BaseModel):
    # order follows protocol Table 4
    name: str
    center_freq: float
    carrier_freq: float = 0
    carrier_rate: float = 0
    sat_longitude: float = 0
    pol_mode: int = 1  # 0=H,1=V (frontend clamps)
    lock_threshold: float = 5.0


# ---- Local Location (place) ----
class PlaceSetReq(BaseModel):
    longitude: float
    latitude: float
    heading: Optional[float] = None  # can be omitted ("fill a space")


# ---- Manual position + speed (dirx) ----
class DirxReq(BaseModel):
    sport_type: str  # a/e/p/l
    az_target: Optional[float] = None
    az_speed: Optional[float] = None
    pitch_target: Optional[float] = None
    pitch_speed: Optional[float] = None
    pol_target: Optional[float] = None
    pol_speed: Optional[float] = None


# ---- Manual speed-only (manual) ----

# ---- LO + Gain ----
class LOSetReq(BaseModel):
    lo_mhz: float
    gain: float
    mode: str = "beacon"  # "beacon" or "dvb"


# ---- Unified antenna action (optional) ----
class AntennaActionReq(BaseModel):
    action: str  # "reset" | "align_star" | "collection" | "stop"


# =========================================================
# Helper: safe send
# =========================================================
def send_frame(frame_type: str, frame_code: str, data: List[str], retries=3, timeout=0.7):
    frame = build_frame(frame_type, frame_code, *data)
    resp = acu.send_and_read(frame, retries=retries, timeout=timeout)
    return frame.strip(), resp


# =========================================================
# REST: Base / existing
# =========================================================
@app.get("/api/ports")
def ports():
    return {"ports": acu_serial.list_ports()}


@app.get("/api/mode")
def mode():
    return {"mode": acu.mode}


@app.post("/api/connect_serial")
def connect_serial(req: ConnectSerialReq):
    global acu
    try:
        acu_serial.connect(req.port, baudrate=req.baudrate, timeout=req.timeout)
        acu = acu_serial
        return {"ok": True, "connected": True, "mode": "serial", "port": req.port}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/connect_tcp")
def connect_tcp(req: ConnectTcpReq):
    global acu
    try:
        tcp_acu.connect(req.host, req.port, timeout=req.timeout)
        acu = tcp_acu
        return {"ok": True, "connected": True, "mode": "tcp",
                "host": req.host, "port": req.port}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/disconnect")
def disconnect():
    acu.disconnect()
    return {"ok": True, "connected": False, "mode": acu.mode}


@app.get("/api/connected")
def connected():
    return {"connected": acu.is_connected(), "mode": acu.mode}


@app.post("/api/send")
def send(req: SendReq):
    try:
        frame, resp = send_frame(req.frame_type, req.frame_code, req.data,
                                retries=req.retries, timeout=req.timeout)
        return {"frame": frame, "response": resp, "parsed": parse_show(resp)}
    except TimeoutError as e:
        raise HTTPException(504, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/status")
def status():
    try:
        frame, resp = send_frame("cmd", "get show", [], retries=3, timeout=0.7)
        return {"frame": frame, "response": resp, "parsed": parse_show(resp)}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Satellite
# =========================================================
@app.get("/api/satellite/get")
def get_satellite():
    try:
        frame, resp = send_frame("cmd", "get sat", [], retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/satellite/set")
def set_satellite(req: SatSetReq):
    try:
        data = [
            req.name,
            f"{req.center_freq:.2f}",
            f"{req.carrier_freq:.2f}",
            f"{req.carrier_rate:.2f}",
            f"{req.sat_longitude:.2f}",
            str(req.pol_mode),
            f"{req.lock_threshold:.2f}",
        ]
        frame, resp = send_frame("cmd", "sat", data, retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Local location (place)
# =========================================================
@app.get("/api/location/get")
def get_location():
    try:
        frame, resp = send_frame("cmd", "get place", [], retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/location/set")
def set_location(req: PlaceSetReq):
    try:
        data = [f"{req.longitude:.6f}", f"{req.latitude:.6f}"]
        if req.heading is not None:
            data.append(f"{req.heading:.2f}")
        frame, resp = send_frame("cmd", "place", data, retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Antenna actions
# =========================================================
@app.post("/api/antenna/reset")
def antenna_reset():
    try:
        frame, resp = send_frame("cmd", "reset", [], retries=3, timeout=2.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/antenna/align_star")
def antenna_align_star():
    try:
        frame, resp = send_frame("cmd", "search", [], retries=3, timeout=2.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/antenna/collection")
def antenna_collection():
    try:
        frame, resp = send_frame("cmd", "stow", [], retries=3, timeout=2.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/antenna/action")
def antenna_action(req: AntennaActionReq):
    try:
        action = req.action.lower().strip()

        if action == "reset":
            return antenna_reset()
        if action in ("align_star", "star", "search_star"):
            return antenna_align_star()
        if action in ("collection", "stow", "stow_collection"):
            return antenna_collection()
        if action == "stop":
            return stop()

        raise HTTPException(400, f"Unknown action: {req.action}")

    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Manual position + speed mode (dirx)
# =========================================================
@app.post("/api/manual/dirx")
def manual_dirx(req: DirxReq):
    """
    Uses protocol 'dirx' with 'fill a space' support:
    if a field is None -> not included at the end.
    """
    try:
        data = [req.sport_type]

        def add(v):
            if v is None:
                return
            data.append(f"{v:.2f}")

        add(req.az_target)
        add(req.az_speed)
        add(req.pitch_target)
        add(req.pitch_speed)
        add(req.pol_target)
        add(req.pol_speed)

        frame, resp = send_frame("cmd", "dirx", data, retries=3, timeout=1.5)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Manual speed-only mode (manual,<dir>,<speed>)
# =========================================================

class ManualSpeedReq(BaseModel):
    direction_code: str
    speed: float

@app.post("/api/manual/speed")
def manual_speed(req: ManualSpeedReq):
    """
    Protocol Section 7 / Table 6:
      manual,<direction_code>,<speed>
    Example:
      $cmd,manual,L,2.50,*hh
    """
    try:
        data = [req.direction_code, f"{req.speed:.2f}"]
        frame, resp = send_frame("cmd", "manual", data, retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Stop
# =========================================================
@app.post("/api/stop")
def stop():
    try:
        frame, resp = send_frame("cmd", "stop", [], retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# REST: Local oscillator + gain
# =========================================================
@app.get("/api/lo/get")
def get_lo():
    try:
        f1, r1 = send_frame("cmd", "get beacon", [], retries=3, timeout=1.0)
        f2, r2 = send_frame("cmd", "get dvb", [], retries=3, timeout=1.0)
        return {
            "beacon": {"frame": f1, "response": r1},
            "dvb": {"frame": f2, "response": r2},
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/lo/set")
def set_lo(req: LOSetReq):
    try:
        code = "set beacon" if req.mode.lower() == "beacon" else "set dvb"
        data = [f"{req.lo_mhz:.0f}", f"{req.gain:.2f}"]
        frame, resp = send_frame("cmd", code, data, retries=3, timeout=1.0)
        return {"frame": frame, "response": resp}
    except Exception as e:
        raise HTTPException(400, str(e))


# =========================================================
# WebSocket: existing SHOW stream
# =========================================================
@app.websocket("/ws/show")
async def ws_show(websocket: WebSocket):
    await websocket.accept()
    print("WS /ws/show accepted")

    interval_sec = 0.2  # 5 Hz

    try:
        while True:
            if not acu.is_connected():
                await websocket.send_json({
                    "connected": False,
                    "mode": acu.mode,
                    "note": "ACU not connected"
                })
                await asyncio.sleep(1.0)
                continue

            try:
                frame = "$cmd,get show,*3f\r\n"
                resp = await asyncio.to_thread(acu.send_and_read, frame, 3, 5)
                parsed = parse_show(resp)

                await websocket.send_json({
                    "connected": True,
                    "mode": acu.mode,
                    "frame": frame.strip(),
                    "raw": resp,
                    "parsed": parsed
                })

            except Exception as e:
                traceback.print_exc()
                await websocket.send_json({
                    "connected": True,
                    "mode": acu.mode,
                    "error": str(e)
                })

            await asyncio.sleep(interval_sec)

    except WebSocketDisconnect:
        print("WS /ws/show disconnected")


# =========================================================
# WebSocket: Satellite stream
# =========================================================
@app.websocket("/ws/sat")
async def ws_sat(websocket: WebSocket):
    await websocket.accept()
    print("WS /ws/sat accepted")

    try:
        while True:
            if not acu.is_connected():
                await websocket.send_json({"connected": False})
                await asyncio.sleep(1)
                continue

            try:
                frame, resp = await asyncio.to_thread(send_frame, "cmd", "get sat", [], 3, 1.0)
                await websocket.send_json({"connected": True, "frame": frame, "raw": resp})
            except Exception as e:
                await websocket.send_json({"connected": True, "error": str(e)})

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        print("WS /ws/sat disconnected")


# =========================================================
# WebSocket: Local location stream
# =========================================================
@app.websocket("/ws/location")
async def ws_location(websocket: WebSocket):
    await websocket.accept()
    print("WS /ws/location accepted")

    try:
        while True:
            if not acu.is_connected():
                await websocket.send_json({"connected": False})
                await asyncio.sleep(1)
                continue

            try:
                frame, resp = await asyncio.to_thread(send_frame, "cmd", "get place", [], 3, 1.0)
                await websocket.send_json({"connected": True, "frame": frame, "raw": resp})
            except Exception as e:
                await websocket.send_json({"connected": True, "error": str(e)})

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        print("WS /ws/location disconnected")


# =========================================================
# WebSocket: Local oscillator + gain stream
# =========================================================
@app.websocket("/ws/lo")
async def ws_lo(websocket: WebSocket):
    await websocket.accept()
    print("WS /ws/lo accepted")

    try:
        while True:
            if not acu.is_connected():
                await websocket.send_json({"connected": False})
                await asyncio.sleep(1)
                continue

            try:
                f1, r1 = await asyncio.to_thread(send_frame, "cmd", "get beacon", [], 3, 1.0)
                f2, r2 = await asyncio.to_thread(send_frame, "cmd", "get dvb", [], 3, 1.0)
                await websocket.send_json({
                    "connected": True,
                    "beacon": {"frame": f1, "raw": r1},
                    "dvb": {"frame": f2, "raw": r2},
                })
            except Exception as e:
                await websocket.send_json({"connected": True, "error": str(e)})

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        print("WS /ws/lo disconnected")

// ============================
// Config
// ============================
const API_BASE = "http://127.0.0.1:8000";
const WS_URL   = "ws://127.0.0.1:8000/ws/show";
const WS_SAT   = "ws://127.0.0.1:8000/ws/sat";
const WS_PLACE = "ws://127.0.0.1:8000/ws/location";
const WS_LO    = "ws://127.0.0.1:8000/ws/lo";

// ============================
// DOM
// ============================
const serialPortSelect = document.getElementById("serialPortSelect");
const btnRefreshPorts  = document.getElementById("btnRefreshPorts");
const btnConnectSerial = document.getElementById("btnConnectSerial");
const btnConnectTcp    = document.getElementById("btnConnectTcp");
const btnDisconnect    = document.getElementById("btnDisconnect");
const tcpTargetInput   = document.getElementById("tcpTarget");

const pillStatus       = document.getElementById("pillStatus");
const pillMode         = document.getElementById("pillMode");

const logConsole       = document.getElementById("logConsole");
const btnClearLog      = document.getElementById("btnClearLog");
const btnCopyLog       = document.getElementById("btnCopyLog");

const toggleStream     = document.getElementById("toggleStream");

const btnSendCustom    = document.getElementById("btnSendCustom");
const customCode       = document.getElementById("customCode");
const customData       = document.getElementById("customData");
const customRetries    = document.getElementById("customRetries");
const customTimeout    = document.getElementById("customTimeout");

const navItems         = document.querySelectorAll(".nav-item");
const pages            = document.querySelectorAll(".page");

const toggleTheme      = document.getElementById("toggleTheme");

// Satellite DOM
const satRaw = document.getElementById("satRaw");
const satForm = document.getElementById("satForm");

// Place DOM
const placeRaw = document.getElementById("placeRaw");
const placeForm = document.getElementById("placeForm");

// Manual DOM
const manualForm = document.getElementById("manualForm");
const btnStopManual = document.getElementById("btnStopManual");
const btnResetManual = document.getElementById("btnResetManual");
const btnAlignStarManual = document.getElementById("btnAlignStarManual");
const btnStowManual = document.getElementById("btnStowManual");

const btnSendSpeedOnly = document.getElementById("btnSendSpeedOnly");

// LO DOM
const loRaw = document.getElementById("loRaw");
const loForm = document.getElementById("loForm");

// metric ids must match backend parse_show keys
const metricKeys = [
  "preset_azimuth","preset_pitch","preset_polarization",
  "current_azimuth","current_pitch","current_polarization",
  "antenna_status","carrier_heading","carrier_pitch","carrier_roll",
  "longitude","latitude","gps_status","limit_info","alert_info",
  "agc_level","az_pot","pitch_pot","time","checksum"
];

// ============================
// Helpers
// ============================
function log(line){
  if(!logConsole) return;
  const ts = new Date().toLocaleTimeString();
  logConsole.textContent += `[${ts}] ${line}\n`;
  logConsole.scrollTop = logConsole.scrollHeight;
}

function setStatus(connected, mode="-"){
  if(!pillStatus || !pillMode) return;
  pillStatus.textContent = connected ? "connected" : "disconnected";
  pillStatus.classList.toggle("connected", connected);
  pillStatus.classList.toggle("disconnected", !connected);
  pillMode.textContent = `mode: ${mode}`;
}

async function apiGet(path){
  const r = await fetch(`${API_BASE}${path}`);
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPost(path, body){
  const r = await fetch(`${API_BASE}${path}`, {
    method:"POST",
    headers:{ "Content-Type":"application/json"},
    body: JSON.stringify(body)
  });
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

function fillMetrics(parsed){
  metricKeys.forEach(k=>{
    const el = document.getElementById(k);
    if(!el) return;
    const v = parsed?.[k] ?? "-";
    el.textContent = v === "" ? "-" : v;
  });
}

// for fill-a-space optional numeric fields
function valOrNull(id){
  const el = document.getElementById(id);
  if(!el) return null;
  const s = el.value.trim();
  return s === "" ? null : Number(s);
}

// ============================
// Sidebar Navigation
// ============================
function showPage(pageId){
  pages.forEach(p => p.classList.remove("active"));
  const target = document.getElementById(`page-${pageId}`);
  if(target) target.classList.add("active");

  navItems.forEach(n => n.classList.remove("active"));
  navItems.forEach(n => {
    if(n.dataset.page === pageId) n.classList.add("active");
  });
}

navItems.forEach(btn=>{
  btn.addEventListener("click", ()=> showPage(btn.dataset.page));
});

// ============================
// Theme toggle
// ============================
function setTheme(isDark){
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  toggleTheme.checked = isDark;
  localStorage.setItem("theme", isDark ? "dark" : "light");
}
toggleTheme.addEventListener("change", e => setTheme(e.target.checked));

// ============================
// Ports
// ============================
async function refreshPorts(){
  try{
    const data = await apiGet("/api/ports");
    serialPortSelect.innerHTML = `<option value="">-- Serial Ports --</option>`;
    data.ports.forEach(p=>{
      const opt = document.createElement("option");
      opt.value = p.device;
      opt.textContent = `${p.device} — ${p.description}`;
      serialPortSelect.appendChild(opt);
    });
    log("Ports refreshed.");
  }catch(e){
    log("ERROR ports: " + e.message);
  }
}

// ============================
// Connect / Disconnect
// ============================
btnConnectSerial.onclick = async ()=>{
  const port = serialPortSelect.value;
  if(!port){
    log("Pick a serial port first.");
    return;
  }
  try{
    const res = await apiPost("/api/connect_serial", {
      port, baudrate:38400, timeout:0.5
    });
    setStatus(true, res.mode || "serial");
    log(`Serial connected: ${port}`);
  }catch(e){
    setStatus(false, "-");
    log("ERROR connect serial: " + e.message);
  }
};

btnConnectTcp.onclick = async ()=>{
  const target = tcpTargetInput.value.trim();
  if(!target.includes(":")){
    log("TCP target must be like ip:port");
    return;
  }
  const [host, portStr] = target.split(":");
  const port = Number(portStr);
  try{
    await apiPost("/api/connect_tcp", { host, port, timeout:2.0 });
    setStatus(true, "tcp");
    log(`TCP connected: ${host}:${port}`);
  }catch(e){
    setStatus(false, "-");
    log("ERROR connect tcp: " + e.message);
  }
};

btnDisconnect.onclick = async ()=>{
  try{
    await apiPost("/api/disconnect", {});
    setStatus(false, "-");
    log("Disconnected.");
  }catch(e){
    log("ERROR disconnect: " + e.message);
  }
};

// ============================
// Commands (generic)
// ============================
async function sendCommand(frame_code, dataFields=[]){
  try{
    const res = await apiPost("/api/send", {
      frame_type:"cmd",
      frame_code,
      data:dataFields,
      retries:3,
      timeout:0.5
    });
    log(`[TX] ${res.frame}`);
    log(`[RX] ${res.response}`);
    if(res.parsed) fillMetrics(res.parsed);
  }catch(e){
    log("ERROR send: " + e.message);
  }
}

document.querySelectorAll(".btn.cmd").forEach(btn=>{
  btn.onclick = ()=> sendCommand(btn.dataset.cmd || "");
});

// Custom command
btnSendCustom.onclick = ()=>{
  const code = customCode.value.trim();
  if(!code){
    log("Custom frame_code empty.");
    return;
  }
  const data = customData.value.trim()
    ? customData.value.split(",").map(s=>s.trim()).filter(Boolean)
    : [];
  sendCustom(code, data);
};

async function sendCustom(frame_code, dataFields){
  try{
    const res = await apiPost("/api/send", {
      frame_type:"cmd",
      frame_code,
      data:dataFields,
      retries:Number(customRetries.value || 3),
      timeout:Number(customTimeout.value || 0.5)
    });
    log(`[TX] ${res.frame}`);
    log(`[RX] ${res.response}`);
    if(res.parsed) fillMetrics(res.parsed);
  }catch(e){
    log("ERROR custom send: " + e.message);
  }
}

// ============================
// Satellite form submit
// ============================
if(satForm){
  satForm.addEventListener("submit", async (e)=>{
    e.preventDefault();
    try{
      let pol = Number(document.getElementById("sat_pol_mode").value || 0);
      pol = (pol <= 0 ? 0 : 1); // ✅ clamp 0/1 per doc

      const body = {
        name: document.getElementById("sat_name").value.trim(),
        center_freq: Number(document.getElementById("sat_center_freq").value),
        carrier_freq: Number(document.getElementById("sat_carrier_freq").value || 0),
        carrier_rate: Number(document.getElementById("sat_carrier_rate").value || 0),
        sat_longitude: Number(document.getElementById("sat_longitude").value || 0),
        pol_mode: pol,
        lock_threshold: Number(document.getElementById("sat_lock_threshold").value || 5.0),
      };
      const res = await apiPost("/api/satellite/set", body);
      log(`[TX][SAT SET] ${res.frame}`);
      log(`[RX][SAT SET] ${res.response}`);
    }catch(err){
      log("ERROR sat set: " + err.message);
    }
  });
}

// ============================
// Place form submit
// ============================
if(placeForm){
  placeForm.addEventListener("submit", async (e)=>{
    e.preventDefault();
    try{
      const headingVal = document.getElementById("place_heading").value.trim();
      const body = {
        longitude: Number(document.getElementById("place_longitude").value),
        latitude: Number(document.getElementById("place_latitude").value),
      };
      if(headingVal !== "") body.heading = Number(headingVal);

      const res = await apiPost("/api/location/set", body);
      log(`[TX][PLACE SET] ${res.frame}`);
      log(`[RX][PLACE SET] ${res.response}`);
    }catch(err){
      log("ERROR place set: " + err.message);
    }
  });
}

// ============================
// Manual dirx submit
// ============================
if(manualForm){
  manualForm.addEventListener("submit", async (e)=>{
    e.preventDefault();
    try{
      const body = {
        sport_type: document.getElementById("manual_sport_type").value,
        az_target: valOrNull("manual_az_target"),
        az_speed: valOrNull("manual_az_speed"),
        pitch_target: valOrNull("manual_pitch_target"),
        pitch_speed: valOrNull("manual_pitch_speed"),
        pol_target: valOrNull("manual_pol_target"),
        pol_speed: valOrNull("manual_pol_speed"),
      };

      const res = await apiPost("/api/manual/dirx", body);
      log(`[TX][DIRX] ${res.frame}`);
      log(`[RX][DIRX] ${res.response}`);
    }catch(err){
      log("ERROR manual dirx: " + err.message);
    }
  });
}

// Manual action buttons
if(btnStopManual) btnStopManual.onclick = ()=> sendCommand("stop");

if(btnResetManual){
  btnResetManual.onclick = ()=> apiPost("/api/antenna/reset", {}).then(r=>{
    log(`[TX][RESET] ${r.frame}`); log(`[RX][RESET] ${r.response}`);
  }).catch(e=>log("ERROR reset: " + e.message));
}

if(btnAlignStarManual){
  btnAlignStarManual.onclick = ()=> apiPost("/api/antenna/align_star", {}).then(r=>{
    log(`[TX][SEARCH] ${r.frame}`); log(`[RX][SEARCH] ${r.response}`);
  }).catch(e=>log("ERROR search: " + e.message));
}

if(btnStowManual){
  btnStowManual.onclick = ()=> apiPost("/api/antenna/collection", {}).then(r=>{
    log(`[TX][STOW] ${r.frame}`); log(`[RX][STOW] ${r.response}`);
  }).catch(e=>log("ERROR stow: " + e.message));
}

// ============================
// Manual speed-only button
// ============================
if(btnSendSpeedOnly){
  btnSendSpeedOnly.onclick = async ()=>{
    try{
      const dir = document.getElementById("speed_direction_code").value;
      const speedStr = document.getElementById("speed_value").value.trim();

      if(speedStr === ""){
        log("Speed value required.");
        return;
      }

      const body = {
        direction_code: dir,
        speed: Number(speedStr)
      };

      const res = await apiPost("/api/manual/speed", body);
      log(`[TX][MANUAL SPEED] ${res.frame}`);
      log(`[RX][MANUAL SPEED] ${res.response}`);

    }catch(err){
      log("ERROR manual speed-only: " + err.message);
    }
  };
}

// ============================
// LO form submit
// ============================
if(loForm){
  loForm.addEventListener("submit", async (e)=>{
    e.preventDefault();
    try{
      const body = {
        mode: document.getElementById("lo_mode").value,
        lo_mhz: Number(document.getElementById("lo_mhz").value),
        gain: Number(document.getElementById("lo_gain").value),
      };
      const res = await apiPost("/api/lo/set", body);
      log(`[TX][LO SET] ${res.frame}`);
      log(`[RX][LO SET] ${res.response}`);
    }catch(err){
      log("ERROR lo set: " + err.message);
    }
  });
}

// ============================
// Log buttons
// ============================
if(btnClearLog) btnClearLog.onclick = ()=> logConsole.textContent = "";

if(btnCopyLog){
  btnCopyLog.onclick = async ()=>{
    await navigator.clipboard.writeText(logConsole.textContent);
    log("Log copied to clipboard.");
  };
}

// ============================
// WebSockets
// ============================
let wsShow = null;
function startWsShow(){
  wsShow = new WebSocket(WS_URL);

  wsShow.onopen = ()=> log("WS /ws/show connected.");

  wsShow.onclose = ()=> {
    log("WS /ws/show closed. retrying...");
    setTimeout(startWsShow, 1500);
  };

  wsShow.onerror = ()=> log("WS /ws/show error.");

  wsShow.onmessage = (msg)=> {
    if(toggleStream && !toggleStream.checked) return;
    try{
      const data = JSON.parse(msg.data);

      if(data.connected === false){
        setStatus(false, data.mode || "-");
        return;
      }

      setStatus(true, data.mode || "serial/tcp");

      if(data.parsed){
        fillMetrics(data.parsed);
        const raw = data.parsed.raw || data.raw || "";
        if(raw) log(`[WS][SHOW] ${raw}`);
      }

      if(data.error){
        log(`[WS][SHOW][ERR] ${data.error}`);
      }
    }catch(e){
      log("WS show parse error: " + e.message);
    }
  };
}

// Satellite WS
let wsSat = null;
function startWsSat(){
  if(!satRaw) return;
  wsSat = new WebSocket(WS_SAT);

  wsSat.onopen = ()=> log("WS /ws/sat connected.");
  wsSat.onclose = ()=> setTimeout(startWsSat, 2000);
  wsSat.onerror = ()=> log("WS /ws/sat error.");

  wsSat.onmessage = (msg)=>{
    try{
      const data = JSON.parse(msg.data);
      if(data.connected === false) return;

      if(data.raw){
        satRaw.textContent = data.raw;
        log(`[WS][SAT] ${data.raw}`);
      }
      if(data.error) log(`[WS][SAT][ERR] ${data.error}`);
    }catch(e){
      log("WS sat parse error: " + e.message);
    }
  };
}

// Place WS
let wsPlace = null;
function startWsPlace(){
  if(!placeRaw) return;
  wsPlace = new WebSocket(WS_PLACE);

  wsPlace.onopen = ()=> log("WS /ws/location connected.");
  wsPlace.onclose = ()=> setTimeout(startWsPlace, 2000);
  wsPlace.onerror = ()=> log("WS /ws/location error.");

  wsPlace.onmessage = (msg)=>{
    try{
      const data = JSON.parse(msg.data);
      if(data.connected === false) return;

      if(data.raw){
        placeRaw.textContent = data.raw;
        log(`[WS][PLACE] ${data.raw}`);
      }
      if(data.error) log(`[WS][PLACE][ERR] ${data.error}`);
    }catch(e){
      log("WS place parse error: " + e.message);
    }
  };
}

// LO WS
let wsLo = null;
function startWsLo(){
  if(!loRaw) return;
  wsLo = new WebSocket(WS_LO);

  wsLo.onopen = ()=> log("WS /ws/lo connected.");
  wsLo.onclose = ()=> setTimeout(startWsLo, 2000);
  wsLo.onerror = ()=> log("WS /ws/lo error.");

  wsLo.onmessage = (msg)=>{
    try{
      const data = JSON.parse(msg.data);
      if(data.connected === false) return;

      if(data.beacon?.raw || data.dvb?.raw){
        loRaw.textContent =
          `BEACON:\n${data.beacon?.raw || "-"}\n\nDVB:\n${data.dvb?.raw || "-"}`;
        log(`[WS][LO] beacon=${data.beacon?.raw || "-"} dvb=${data.dvb?.raw || "-"}`);
      }
      if(data.error) log(`[WS][LO][ERR] ${data.error}`);
    }catch(e){
      log("WS lo parse error: " + e.message);
    }
  };
}

// ============================
// Init
// ============================
btnRefreshPorts.onclick = refreshPorts;
refreshPorts();

startWsShow();
startWsSat();
startWsPlace();
startWsLo();

setStatus(false,"-");
showPage("dashboard");
log("UI ready.");

const savedTheme = localStorage.getItem("theme");
setTheme(savedTheme ? savedTheme === "dark" : false); // default LIGHT

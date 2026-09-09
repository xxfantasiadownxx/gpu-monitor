#!/usr/bin/env python3
"""
GPU Monitor Server
Runs nvidia-smi and exposes data via a local HTTP API.
Usage: python gpu_server.py
Then visit http://localhost:10101 in your browser.
"""

import subprocess
import json
import sys
import os
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 10101
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_container_pid_map():
    """
    Returns a dict mapping every host PID -> container name.
    Walks each running container's full process tree via docker top.
    """
    pid_map = {}
    try:
        # Get all running container names
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return pid_map

        container_names = [n.strip() for n in result.stdout.strip().splitlines() if n.strip()]

        for name in container_names:
            # Get all PIDs in this container (full process tree on host)
            top = subprocess.run(
                ["docker", "top", name, "-eo", "pid"],
                capture_output=True, text=True, timeout=5
            )
            if top.returncode != 0:
                continue
            lines = top.stdout.strip().splitlines()
            # First line is header "PID", skip it
            for line in lines[1:]:
                pid = line.strip()
                if pid.isdigit():
                    pid_map[pid] = name

    except Exception as e:
        print(f"[WARN] Container PID map failed: {e}", flush=True)

    return pid_map


def resolve_process(proc, pid_map):
    """
    Given a process dict from nvidia-smi and the pid->container map,
    return a display name like 'jellyfin > ffmpeg' or 'host > python'.
    """
    pid = proc.get("pid", "")
    raw_name = proc.get("name", "N/A")
    short_name = raw_name.split("/")[-1]  # basename only

    container = pid_map.get(pid)
    if container:
        # Clean up common auto-generated compose name suffixes (e.g. jellyfin-1 -> jellyfin)
        display_container = container.rstrip("-0123456789").rstrip("-")
        return {
            "pid": pid,
            "container": display_container,
            "process": short_name,
            "display": f"{display_container} > {short_name}",
            "type": proc.get("type", "C"),
            "used_memory": proc.get("used_memory", "N/A"),
        }
    else:
        return {
            "pid": pid,
            "container": "host",
            "process": short_name,
            "display": f"host > {short_name}",
            "type": proc.get("type", "C"),
            "used_memory": proc.get("used_memory", "N/A"),
        }


def run_nvidia_smi():
    try:
        result = subprocess.run(
            ["nvidia-smi", "-q", "-x"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"error": f"nvidia-smi failed: {result.stderr}"}

        root = ET.fromstring(result.stdout)

        # Build container PID map once per poll
        pid_map = get_container_pid_map()

        gpus = []

        for gpu in root.findall("gpu"):
            def get(tag, subtag=None):
                el = gpu.find(tag)
                if el is None:
                    return "N/A"
                if subtag:
                    sub = el.find(subtag)
                    return sub.text.strip() if sub is not None and sub.text else "N/A"
                return el.text.strip() if el.text else "N/A"

            util = gpu.find("utilization")
            gpu_util = util.find("gpu_util").text.strip() if util is not None else "N/A"
            mem_util = util.find("memory_util").text.strip() if util is not None else "N/A"

            mem = gpu.find("fb_memory_usage")
            mem_total = mem.find("total").text.strip() if mem is not None else "N/A"
            mem_used  = mem.find("used").text.strip()  if mem is not None else "N/A"
            mem_free  = mem.find("free").text.strip()  if mem is not None else "N/A"

            temp = gpu.find("temperature")
            gpu_temp = temp.find("gpu_temp").text.strip() if temp is not None else "N/A"

            # Try all known power section tag names across driver versions and GPU families
            power = (
                gpu.find("power_readings") or
                gpu.find("gpu_power_readings") or
                gpu.find("power_management") or
                gpu.find("instant_power_readings")
            )
            def get_power_val(section, *tags):
                if section is None:
                    return "N/A"
                for tag in tags:
                    el = section.find(tag)
                    if el is not None and el.text and el.text.strip() not in ("N/A", "[N/A]", ""):
                        return el.text.strip()
                return "N/A"
            power_draw  = get_power_val(power, "power_draw", "instant_power_draw", "average_power_draw")
            power_limit = get_power_val(power, "power_limit", "current_power_limit", "enforced_power_limit", "default_power_limit")

            clocks = gpu.find("clocks")
            sm_clock  = clocks.find("sm_clock").text.strip()  if clocks is not None else "N/A"
            mem_clock = clocks.find("mem_clock").text.strip() if clocks is not None else "N/A"

            fan_speed = get("fan_speed")

            # Parse raw processes then resolve container ownership
            raw_procs = []
            procs_el = gpu.find("processes")
            if procs_el is not None:
                for proc in procs_el.findall("process_info"):
                    def pget(tag):
                        el = proc.find(tag)
                        return el.text.strip() if el is not None and el.text else "N/A"
                    raw_procs.append({
                        "pid":         pget("pid"),
                        "name":        pget("process_name"),
                        "type":        pget("type"),
                        "used_memory": pget("used_memory"),
                    })

            processes = [resolve_process(p, pid_map) for p in raw_procs]

            gpus.append({
                "id":                 get("minor_number"),
                "name":               get("product_name"),
                "uuid":               get("uuid"),
                "driver_version":     root.find("driver_version").text.strip() if root.find("driver_version") is not None else "N/A",
                "cuda_version":       root.find("cuda_version").text.strip()    if root.find("cuda_version")    is not None else "N/A",
                "gpu_utilization":    gpu_util,
                "memory_utilization": mem_util,
                "memory_total":       mem_total,
                "memory_used":        mem_used,
                "memory_free":        mem_free,
                "temperature":        gpu_temp,
                "power_draw":         power_draw,
                "power_limit":        power_limit,
                "sm_clock":           sm_clock,
                "mem_clock":          mem_clock,
                "fan_speed":          fan_speed,
                "processes":          processes,
            })

        return {"gpus": gpus, "timestamp": __import__("datetime").datetime.now().isoformat()}

    except FileNotFoundError:
        return {"error": "nvidia-smi not found. Make sure --gpus all is passed to docker run."}
    except subprocess.TimeoutExpired:
        return {"error": "nvidia-smi timed out."}
    except Exception as e:
        return {"error": str(e)}


# --- Background cache ---
# Runs nvidia-smi on a timer so HTTP requests always return instantly
# from the last known good result, preventing HA "unavailable" flicker.

import threading
import time

_cache_lock = threading.Lock()
_cache = {"data": None, "last_update": 0}
CACHE_TTL = 2  # seconds between nvidia-smi polls


def get_cached_data():
    with _cache_lock:
        return _cache["data"] or {"error": "No data yet, waiting for first poll"}


def background_poller():
    while True:
        try:
            data = run_nvidia_smi()
            with _cache_lock:
                _cache["data"] = data
                _cache["last_update"] = time.time()
        except Exception as e:
            print(f"[POLL ERROR] {e}", flush=True)
        time.sleep(CACHE_TTL)


class GPUHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/gpu_monitor.html")
            self.end_headers()
            return

        if path == "/gpu_monitor.html":
            html_path = os.path.join(BASE_DIR, "gpu_monitor.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"gpu_monitor.html not found in container.")
            return

        if path == "/api/gpu":
            data = get_cached_data()
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/gpu/simple":
            data = get_cached_data()
            if "error" in data:
                simple = {"error": data["error"]}
            elif "gpus" in data and data["gpus"]:
                g = data["gpus"][0]
                procs = g.get("processes", [])
                simple = {
                    "gpu_util":      g["gpu_utilization"].replace(" %", ""),
                    "mem_used":      g["memory_used"],
                    "mem_total":     g["memory_total"],
                    "mem_util":      g["memory_utilization"].replace(" %", ""),
                    "temperature":   g["temperature"].replace(" C", ""),
                    "power_draw":    g["power_draw"].replace(" W", "") if g["power_draw"] != "N/A" else "N/A",
                    "power_limit":   g["power_limit"].replace(" W", "") if g["power_limit"] != "N/A" else "N/A",
                    "fan_speed":     g["fan_speed"].replace(" %", "") if g["fan_speed"] != "N/A" else "N/A",
                    "sm_clock":      g["sm_clock"].replace(" MHz", "") if g["sm_clock"] != "N/A" else "N/A",
                    "process_count": len(procs),
                    "processes":     ", ".join(p["display"] for p in procs) if procs else "Idle",
                }
            else:
                simple = {"error": "no GPU data"}
            body = json.dumps(simple).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[REQUEST] {format % args}", flush=True, file=sys.stdout)


if __name__ == "__main__":
    print(f"✅ GPU Monitor server starting on 0.0.0.0:{PORT}", flush=True)
    print(f"   Dashboard: http://localhost:{PORT}", flush=True)
    print(f"   API:       http://localhost:{PORT}/api/gpu", flush=True)
    print(f"   Press Ctrl+C to stop\n", flush=True)
    # Start background poller thread
    t = threading.Thread(target=background_poller, daemon=True)
    t.start()
    print(f"   Background poller started (every {CACHE_TTL}s)", flush=True)

    server = HTTPServer(("0.0.0.0", PORT), GPUHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

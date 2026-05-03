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


def run_nvidia_smi():
    try:
        result = subprocess.run(
            ["nvidia-smi", "-q", "-x"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"error": f"nvidia-smi failed: {result.stderr}"}

        root = ET.fromstring(result.stdout)
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
            mem_used = mem.find("used").text.strip() if mem is not None else "N/A"
            mem_free = mem.find("free").text.strip() if mem is not None else "N/A"

            temp = gpu.find("temperature")
            gpu_temp = temp.find("gpu_temp").text.strip() if temp is not None else "N/A"

            power = gpu.find("power_readings") or gpu.find("gpu_power_readings")
            power_draw = power.find("power_draw").text.strip() if power is not None and power.find("power_draw") is not None else "N/A"
            power_limit = power.find("power_limit").text.strip() if power is not None and power.find("power_limit") is not None else "N/A"

            clocks = gpu.find("clocks")
            sm_clock = clocks.find("sm_clock").text.strip() if clocks is not None else "N/A"
            mem_clock = clocks.find("mem_clock").text.strip() if clocks is not None else "N/A"

            fan_speed = get("fan_speed")

            processes = []
            procs_el = gpu.find("processes")
            if procs_el is not None:
                for proc in procs_el.findall("process_info"):
                    def pget(tag):
                        el = proc.find(tag)
                        return el.text.strip() if el is not None and el.text else "N/A"
                    processes.append({
                        "pid": pget("pid"),
                        "name": pget("process_name"),
                        "type": pget("type"),
                        "used_memory": pget("used_memory"),
                    })

            gpus.append({
                "id": get("minor_number"),
                "name": get("product_name"),
                "uuid": get("uuid"),
                "driver_version": root.find("driver_version").text.strip() if root.find("driver_version") is not None else "N/A",
                "cuda_version": root.find("cuda_version").text.strip() if root.find("cuda_version") is not None else "N/A",
                "gpu_utilization": gpu_util,
                "memory_utilization": mem_util,
                "memory_total": mem_total,
                "memory_used": mem_used,
                "memory_free": mem_free,
                "temperature": gpu_temp,
                "power_draw": power_draw,
                "power_limit": power_limit,
                "sm_clock": sm_clock,
                "mem_clock": mem_clock,
                "fan_speed": fan_speed,
                "processes": processes,
            })

        return {"gpus": gpus, "timestamp": __import__("datetime").datetime.now().isoformat()}

    except FileNotFoundError:
        return {"error": "nvidia-smi not found. Make sure --gpus all is passed to docker run."}
    except subprocess.TimeoutExpired:
        return {"error": "nvidia-smi timed out."}
    except Exception as e:
        return {"error": str(e)}


class GPUHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        # Redirect root to the dashboard
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/gpu_monitor.html")
            self.end_headers()
            return

        # Serve the HTML dashboard
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

        # API endpoint
        if path == "/api/gpu":
            data = run_nvidia_smi()
            body = json.dumps(data).encode()
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
    server = HTTPServer(("0.0.0.0", PORT), GPUHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

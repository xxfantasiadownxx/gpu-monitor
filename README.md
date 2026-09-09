# 🖥️ GPU Monitor

A lightweight, real-time NVIDIA GPU monitoring dashboard served via Docker. View live utilization, memory, temperature, power, clocks, fan speed, and active processes from any browser on your network.

![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
![NVIDIA](https://img.shields.io/badge/NVIDIA-SMI-green?logo=nvidia)
![Python](https://img.shields.io/badge/python-3.11-yellow?logo=python)

---

## Features

- Live GPU utilization, memory, temperature, power, fan speed, and clock speeds
- Active process table showing what is currently using the GPU
- Color-coded metrics that shift from green → yellow → red as values increase
- Smooth bar animations with no page flicker on refresh
- Adjustable polling interval (1s, 2s, 5s, 10s)
- Multi-GPU support
- Accessible from any device on your network
- No dependencies beyond Python standard library

---

## Requirements

- Docker with the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on the host
- NVIDIA GPU with drivers installed on the host

---

## Quick Start

### Docker Run

```bash
docker run --gpus all --pid=host -p 10101:10101 xxfantasiadownxx/gpu-monitor:latest
```

Then open your browser to:
```
http://YOUR_SERVER_IP:10101
```

### Docker Compose

```yaml
services:
  gpu-monitor:
    image: xxfantasiadownxx/gpu-monitor:latest
    ports:
      - "10101:10101"
    pid: host
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
```

```bash
docker compose up -d
```

---

## Why `--pid=host`

By default, `nvidia-smi` inside a container can only see processes running inside that container — meaning your host GPU processes (games, encoding jobs, ML training, etc.) would show as invisible. The `--pid=host` flag shares the host's process namespace with the container so all GPU activity is visible regardless of where it's running.

---

## Installing the NVIDIA Container Toolkit

If you haven't set this up yet, run the following on your host machine (Ubuntu/Debian):

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

---

## Home Assistant Integration

Since the container exposes a JSON API, you can pull GPU stats directly into Home Assistant using the REST sensor integration.

Add to `configuration.yaml`:

```yaml
sensor:
  - platform: rest
    name: GPU
    resource: http://YOUR_SERVER_IP:10101/api/gpu/simple
    scan_interval: 5
    value_template: "{{ value_json.gpu_util }}"
    json_attributes:
      - mem_used
      - mem_total
      - temperature
      - power
      - fan
      - process_count
      - processes
```

Dashboard Markdown card:

```yaml
type: markdown
title: GPU Monitor
content: >
  **Utilization:** {{ state_attr('sensor.gpu', 'gpu_util') }}
  **Temp:** {{ state_attr('sensor.gpu', 'temperature') }}
  **Memory:** {{ state_attr('sensor.gpu', 'mem_used') }} / {{ state_attr('sensor.gpu', 'mem_total') }}
  **Power:** {{ state_attr('sensor.gpu', 'power') }}
  **Fan:** {{ state_attr('sensor.gpu', 'fan') }}

  **Active Processes:**
  {{ state_attr('sensor.gpu', 'processes') }}
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Redirects to the dashboard |
| `GET /gpu_monitor.html` | Live dashboard UI |
| `GET /api/gpu` | Full GPU data as JSON |

### Example response from `/api/gpu`

```json
{
  "gpus": [
    {
      "id": "0",
      "name": "NVIDIA GeForce GTX 1660 Ti",
      "gpu_utilization": "54 %",
      "memory_used": "3200 MiB",
      "memory_total": "6144 MiB",
      "temperature": "72 C",
      "power_draw": "89.5 W",
      "fan_speed": "65 %",
      "sm_clock": "1845 MHz",
      "processes": [
        {
          "pid": "12345",
          "name": "/usr/bin/ffmpeg",
          "type": "C",
          "used_memory": "1200 MiB"
        }
      ]
    }
  ],
  "timestamp": "2026-05-03T16:23:18.477968"
}
```

---

## Building from Source

```bash
git clone https://github.com/xxfantasiadownxx/gpu-monitor.git
cd gpu-monitor
docker build -t gpu-monitor .
docker run --gpus all --pid=host -p 10101:10101 gpu-monitor
```

---

## Firewall

If accessing from another machine on your network, make sure port `10101` is open:

```bash
sudo ufw allow 10101
```

---

## License

MIT

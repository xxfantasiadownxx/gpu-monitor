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
    environment:
      - TZ=America/New_York
```

```bash
docker compose up -d
```

---

## Why `--pid=host`

By default, `nvidia-smi` inside a container can only see processes running inside that container — meaning your host GPU processes (games, encoding jobs, ML training, etc.) would show as invisible. The `--pid=host` flag shares the host's process namespace with the container so all GPU activity is visible regardless of where it's running.

---
(this is a 100% vibe coded project)

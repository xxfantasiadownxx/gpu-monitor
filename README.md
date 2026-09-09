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

Add to `rest.yaml`:

```yaml
  - resource: "http://[your-ip]:10101/api/gpu"
    scan_interval: 10
    sensor:
      - name: "GPU Name"
        unique_id: gpu_name
        value_template: "{{ value_json.gpus[0].name }}"

      - name: "GPU Utilization"
        unique_id: gpu_utilization
        value_template: "{{ value_json.gpus[0].gpu_utilization.split(' ')[0] }}"
        unit_of_measurement: "%"
        state_class: measurement

      - name: "GPU Memory Utilization"
        unique_id: gpu_memory_utilization
        value_template: "{{ value_json.gpus[0].memory_utilization.split(' ')[0] }}"
        unit_of_measurement: "%"
        state_class: measurement

      - name: "GPU Memory Total"
        unique_id: gpu_memory_total
        value_template: "{{ value_json.gpus[0].memory_total.split(' ')[0] }}"
        unit_of_measurement: "MiB"
        state_class: measurement

      - name: "GPU Memory Used"
        unique_id: gpu_memory_used
        value_template: "{{ value_json.gpus[0].memory_used.split(' ')[0] }}"
        unit_of_measurement: "MiB"
        state_class: measurement

      - name: "GPU Memory Free"
        unique_id: gpu_memory_free
        value_template: "{{ value_json.gpus[0].memory_free.split(' ')[0] }}"
        unit_of_measurement: "MiB"
        state_class: measurement

      - name: "GPU Temperature"
        unique_id: gpu_temperature
        value_template: "{{ value_json.gpus[0].temperature.split(' ')[0] }}"
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      - name: "GPU Power Draw"
        unique_id: gpu_power_draw
        value_template: >-
          {% set v = value_json.gpus[0].power_draw %}
          {{ v.split(' ')[0] if v != 'N/A' else 'unknown' }}
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement

      - name: "GPU Power Limit"
        unique_id: gpu_power_limit
        value_template: >-
          {% set v = value_json.gpus[0].power_limit %}
          {{ v.split(' ')[0] if v != 'N/A' else 'unknown' }}
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement

      - name: "GPU Fan Speed"
        unique_id: gpu_fan_speed
        value_template: >-
          {% set v = value_json.gpus[0].fan_speed %}
          {{ v.split(' ')[0] if v != 'N/A' else 'unknown' }}
        unit_of_measurement: "%"
        state_class: measurement

      - name: "GPU SM Clock"
        unique_id: gpu_sm_clock
        value_template: "{{ value_json.gpus[0].sm_clock.split(' ')[0] }}"
        unit_of_measurement: "MHz"
        state_class: measurement

      - name: "GPU Memory Clock"
        unique_id: gpu_mem_clock
        value_template: "{{ value_json.gpus[0].mem_clock.split(' ')[0] }}"
        unit_of_measurement: "MHz"
        state_class: measurement

      - name: "GPU Driver Version"
        unique_id: gpu_driver_version
        value_template: "{{ value_json.gpus[0].driver_version }}"

      - name: "GPU CUDA Version"
        unique_id: gpu_cuda_version
        value_template: "{{ value_json.gpus[0].cuda_version }}"

      - name: "GPU Process Count"
        unique_id: gpu_process_count
        value_template: "{{ value_json.gpus[0].processes | length }}"
        state_class: measurement

      - name: "GPU Processes"
        unique_id: gpu_processes
        value_template: >-
          {% set procs = value_json.gpus[0].processes %}
          {{ procs | map(attribute='display') | join(', ') if procs else 'Idle' }}
```

## Building from Source

```bash
git clone https://github.com/xxfantasiadownxx/gpu-monitor.git
cd gpu-monitor
docker build -t gpu-monitor .
docker run --gpus all --pid=host -p 10101:10101 gpu-monitor
```

## License

MIT

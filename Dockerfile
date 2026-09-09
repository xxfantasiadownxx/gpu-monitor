FROM python:3.11-slim
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY gpu_server.py .
COPY gpu_monitor.html .
EXPOSE 10101
CMD ["python", "gpu_server.py"]

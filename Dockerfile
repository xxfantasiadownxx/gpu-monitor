FROM python:3.11-slim
WORKDIR /app
COPY gpu_server.py .
COPY gpu_monitor.html .
EXPOSE 10101
CMD ["python", "gpu_server.py"]

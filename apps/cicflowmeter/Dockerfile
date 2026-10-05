FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# libpcap y tcpdump para la captura en vivo con scapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap0.8 \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Se ejecuta como root: la captura en vivo requiere NET_RAW / NET_ADMIN.
CMD ["python", "main.py"]

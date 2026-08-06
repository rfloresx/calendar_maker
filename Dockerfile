FROM python:3.12-slim

WORKDIR /app

# System deps for Pillow, ephem, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libjpeg-dev zlib1g-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default data path inside the container (mount a volume here)
ENV DATA_PATH=/data

EXPOSE 8080

CMD ["python", "-m", "lib.web.app", "--host", "0.0.0.0", "--port", "8080"]

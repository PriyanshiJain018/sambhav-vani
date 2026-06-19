FROM debian:bookworm-slim

# Install ffmpeg (with libass) + Noto fonts (Devanagari)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto \
    fonts-noto-cjk \
    python3 \
    python3-pip \
    python3-venv \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Verify Devanagari font is present
RUN fc-list | grep -i devanagari || echo "WARNING: Devanagari font not found"

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY main.py .

ENV FONTSDIR=/usr/share/fonts/truetype/noto
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

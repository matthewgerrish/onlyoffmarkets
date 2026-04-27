FROM python:3.12-slim

# System packages needed by lxml + pdfplumber + psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libxml2-dev libxslt1-dev \
      libpq-dev \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Fly.io routes traffic to PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

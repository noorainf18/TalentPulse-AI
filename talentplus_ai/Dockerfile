FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# CPU torch first. The default PyPI wheel is the multi-GB CUDA build and
# blows the Render image build.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render injects PORT. Retry migrate until the new Postgres instance accepts connections.
CMD python manage.py collectstatic --noinput; \
    i=0; \
    until python manage.py migrate --noinput; do \
      i=$((i+1)); \
      if [ "$i" -gt 12 ]; then exit 1; fi; \
      echo "database not ready, retry ${i}"; \
      sleep 5; \
    done; \
    exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application

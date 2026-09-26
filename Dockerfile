FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home app
USER app

EXPOSE 5002

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5002/health')"

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "2", "app:app"]

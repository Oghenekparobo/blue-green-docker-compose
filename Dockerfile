FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
COPY watcher.py .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "/app/watcher.py"]

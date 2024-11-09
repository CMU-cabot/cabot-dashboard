FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY cabot_dashboard_server.py .
COPY users.json .
COPY templates ./templates

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "cabot_dashboard_server:app", "--host", "0.0.0.0", "--port", "8000"]
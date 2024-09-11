FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY cabot_dashboard_client.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "cabot_dashboard_client.py"]
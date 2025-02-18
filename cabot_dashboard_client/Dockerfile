FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /client
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt
COPY *.py .
COPY *.sh .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "cabot_dashboard_client.py"]
# CMD ["python", "-u", "cabot_dashboard_client.py", "-s", "10"]

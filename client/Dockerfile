FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY robot.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "robot.py"]
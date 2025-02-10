FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ssh \
    sudo \
    systemd \
    dbus \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=developer
ARG UID=1000
RUN useradd -m $USERNAME && \
    echo "$USERNAME:$USERNAME" | chpasswd && \
    usermod --shell /bin/bash $USERNAME && \
    usermod -aG sudo $USERNAME && \
    mkdir -p /etc/sudoers.d/ && \
    echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME && \
    usermod  --uid $UID $USERNAME && \
    groupmod --gid $UID $USERNAME

# for systemd
RUN mkdir -p /run/systemd && \
    mkdir -p /run/dbus && \
    mkdir -p ${HOME}/.config/systemd/user

USER $USERNAME
ENV HOME /home/$USERNAME
WORKDIR $HOME

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY *.sh .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "cabot_dashboard_client.py"]
# CMD ["python", "-u", "cabot_dashboard_client.py", "-s", "10"]

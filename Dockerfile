FROM dailyco/pipecat-base:latest
RUN apt-get update && apt-get install cmake libcairo2-dev libjpeg-dev libgif-dev pkg-config libgirepository1.0-dev build-essential meson gstreamer-1.0 python3-gst-1.0 gstreamer1.0-plugins-good -y
COPY ./requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./bot.py bot.py

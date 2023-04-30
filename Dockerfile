FROM python:3

# Path: /app
WORKDIR /app

COPY requirements.txt ./
COPY main.py ./
COPY bot/ ./bot

RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Clear cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Probably not nessesary but just covering my bases
RUN python3 -m pip install -U "discord.py[voice]"

CMD [ "python", "main.py" ]
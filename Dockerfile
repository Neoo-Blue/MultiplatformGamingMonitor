FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gaming_monitor.py .

RUN mkdir -p /app/logs

ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

RUN useradd -m -u 1000 monitor && \
    chown -R monitor:monitor /app
USER monitor

CMD ["python", "-u", "gaming_monitor.py"]

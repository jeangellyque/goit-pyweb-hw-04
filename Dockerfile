FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY main.py index.html message.html error.html style.css logo.png ./

RUN mkdir -p /app/storage
VOLUME ["/app/storage"]

EXPOSE 3000

CMD ["python", "main.py"]

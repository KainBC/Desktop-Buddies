FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir "websockets>=12,<13"

COPY shared/ shared/
COPY relay/ relay/

EXPOSE 8765
CMD ["python", "-m", "relay"]

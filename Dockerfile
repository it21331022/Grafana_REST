FROM python:3.9-slim

WORKDIR /app

COPY inventory_service.py .

RUN pip install flask prometheus_flask_exporter prometheus_client

EXPOSE 9090

CMD ["python", "inventory_service.py"]
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inventory_service.py .

EXPOSE 8080

CMD ["python", "inventory_service.py"]
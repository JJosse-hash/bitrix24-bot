FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY address_ai ./address_ai

EXPOSE 8000
CMD ["uvicorn", "address_ai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

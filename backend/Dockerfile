FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

EXPOSE 8000

# Run FastAPI app exposing to all network interfaces for container mapping
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (single file!)
COPY main.py .

# Copy static assets
COPY assets/ ./assets/

EXPOSE 8000

CMD ["python", "main.py"]

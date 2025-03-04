FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add missing dependencies that are needed based on app.py
RUN pip install --no-cache-dir numpy

COPY . .

# Create directories for uploads and documents
RUN mkdir -p ./uploads ./documents

# Expose port
EXPOSE 5001

# Run the application
CMD ["python", "app.py"]
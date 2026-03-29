# Gateway Service Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the shared package and the gateway code
# These must be copied from the root context
COPY shared/ ./shared/
COPY gateway/ ./gateway/
COPY query/ ./query/
COPY processing/ ./processing/
COPY scripts/ ./scripts/

# Set PYTHONPATH to root so services can import 'shared' and other modules
ENV PYTHONPATH=/app

EXPOSE 8001

# Command to run the FastAPI app
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8001"]

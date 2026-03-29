# Processing Worker Service Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download SpaCy English model for faster startup
RUN python -m spacy download en_core_web_sm

# Copy the shared package and the processing code
COPY shared/ ./shared/
COPY processing/ ./processing/
COPY query/ ./query/
COPY scripts/ ./scripts/

# Set PYTHONPATH to root so services can import 'shared' and other modules
ENV PYTHONPATH=/app

# Command to run the background worker
CMD ["python", "-m", "processing.main"]

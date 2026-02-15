FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set env variables to prevent pyc files and buffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

# Install system dependencies if needed (e.g. for scrypt/authlib)
# RUN apt-get update && apt-get install -y gcc libffi-dev

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for persistent data and uploads
RUN mkdir -p /data
RUN mkdir -p /app/static/uploads

# Expose port
EXPOSE 5000

# Run with Gunicorn for production-grade performance
# Maps to app:app (file:variable)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

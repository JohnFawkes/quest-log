FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set env variables to prevent pyc files and buffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

# Configurable port and timezone
ARG PORT=5000
ENV PORT=${PORT}
ENV TZ=UTC

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r questlog && useradd -r -g questlog -s /bin/false questlog

# Create directory for persistent data and uploads, owned by app user
RUN mkdir -p /data /app/static/uploads \
    && chown -R questlog:questlog /data /app/static/uploads

# Expose port
EXPOSE ${PORT}

# Healthcheck using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /bin/sh -c 'curl -sf http://localhost:${PORT:-5000}/health || exit 1'

# Run as non-root user
USER questlog

# Run with Gunicorn for production-grade performance
CMD /bin/sh -c "gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} --preload app:app"

# Multi-stage Dockerfile for PFA Network Detection Project
# Stage 1: Base image with source code
FROM python:3.9-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the repository once for all stages
RUN git clone https://github.com/Med10S/PFA_project.git . && \
    rm -rf .git

# Stage 2: Development image
FROM base as development

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional ML dependencies if not in requirements.txt
RUN pip install --no-cache-dir \
    scikit-learn==1.3.0 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    tqdm==4.65.0 \
    fastapi==0.100.1 \
    uvicorn==0.23.2

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/app/models
ENV DATA_PATH=/app/data

# Create necessary directories
RUN mkdir -p /app/models /app/data /app/logs

# Expose port for the detection service
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "realtime_detection_service.py"]

# Stage 3: Production image
FROM base as production

# Install only production dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash pfa_user && \
    chown -R pfa_user:pfa_user /app

USER pfa_user

# Set environment variables for production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/app/models
ENV DATA_PATH=/app/data
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "realtime_detection_service:app"]

# Stage 4: Training image (for model retraining)
FROM development as training

# Install additional training dependencies
RUN pip install --no-cache-dir \
    jupyter==1.0.0 \
    ipykernel==6.25.1 \
    plotly==5.15.0

# Copy training scripts
RUN chmod +x retrain_mlp_with_notebook_method.py

# Default command for training
CMD ["python", "retrain_mlp_with_notebook_method.py"]

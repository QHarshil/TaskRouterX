FROM python:3.10-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code including Alembic files
COPY . .

# Removed: RUN alembic upgrade head
# Migrations now run at container startup

# API Service
FROM base as api
EXPOSE 8000
CMD ["bash", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000"]

# Scheduler Service
FROM base as scheduler
CMD ["bash", "-c", "alembic upgrade head && python -m scheduler.runner"]

# Dashboard Service
FROM base as dashboard
RUN pip install --no-cache-dir streamlit pandas altair
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py"]

FROM python:3.10-slim

WORKDIR /app

# Install C compile tools for potential native libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies configuration
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source directories
COPY backend ./backend
COPY frontend ./frontend

# Set working directory to backend
WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "main.py"]

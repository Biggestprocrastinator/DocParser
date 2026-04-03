# Start with a lightweight Python 3.10 image
FROM python:3.10-slim

# Prevent Python from writing .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies specifically needed for OpenCV, Tesseract, and Poppler
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory to /app
WORKDIR /app

# Copy requirement file first to leverage Docker cache
COPY src/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source code from src/ to /app/
COPY src /app/

# Expose the standard FastAPI port
EXPOSE 8000

# The default command runs FastAPI. 
# (For Celery, Render will override this command using the render.yaml config)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

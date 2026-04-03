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
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
# Hugging Face Spaces require running as a non-root user
RUN useradd -m -u 1000 user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory
WORKDIR $HOME/app

# Copy requirement file first to leverage Docker cache
COPY src/requirements.txt $HOME/app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source code
COPY src $HOME/app/

# Make the start script executable and transfer ownership
RUN chmod +x $HOME/app/start.sh && chown -R user:user $HOME/app

# Switch to the non-root user
USER user

# Hugging Face Spaces exposes port 7860
EXPOSE 7860

# Run the startup script which launches both Celery and FastAPI
CMD ["./start.sh"]


#!/bin/bash

# 1. Start the Celery worker in the background (&)
# Using solo pool because Free Tier resources are limited
echo "Starting Celery Worker..."
celery -A tasks worker --loglevel=info --pool=solo &

# 2. Start the FastAPI server in the foreground on HuggingFace's required port
echo "Starting FastAPI Server..."
exec uvicorn main:app --host 0.0.0.0 --port 7860

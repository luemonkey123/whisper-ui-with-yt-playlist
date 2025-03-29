# Use an official Python runtime as the base image
FROM python:3.12.9-slim

# Set the working directory in the container
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    cython3 \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Use pip to install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY main.py .

# Run the script when the container launches
CMD ["python", "main.py"]
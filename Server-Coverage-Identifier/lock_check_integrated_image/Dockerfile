# Use Ubuntu as the base image
FROM ubuntu:latest

# Install necessary packages
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    make \
    gcc \
    git \
    libssl-dev \
    python3 \
    python3-pip \
    python3-venv \
    cpuid \
    stress && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3 -m venv /venv

# Set the virtual environment as the default python
ENV PATH="/venv/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file and install dependencies in the virtual environment
COPY requirements.txt /app/requirements.txt
RUN /venv/bin/pip install --upgrade pip && /venv/bin/pip install -r /app/requirements.txt

COPY lock-3.c /app/
COPY check.c /app/
COPY cacheutils.h /app/

# Build C projects
RUN gcc -o lock-3 lock-3.c
RUN gcc -o check check.c

# Copy the Flask script to the container
COPY flask_app.py /app/

# Expose the port the app runs on
EXPOSE 8080

# Set the Flask app to run when the container launches
CMD ["/venv/bin/python", "flask_app.py"]


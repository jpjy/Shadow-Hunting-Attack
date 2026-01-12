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

# Copy the LLCFeasible directory and necessary files into the container at /app
COPY LLCFeasible/ /app/LLCFeasible/
COPY lock-3.c /app/
COPY check.c /app/
COPY cacheutils.h /app/
COPY common.h /app/
COPY timer.c /app/
COPY timer /app/

# Build C projects
RUN gcc -o lock-3 lock-3.c
RUN gcc -o check check.c

# Ensure symbolic links are properly set
RUN ln -sfn /app/LLCFeasible/extern/PTEditor/ptedit_header.h /app/LLCFeasible/include/ptedit_header.h && \
    rm -rf /app/LLCFeasible/build && mkdir /app/LLCFeasible/build && cd /app/LLCFeasible/build && cmake .. && make

# Copy the Flask script to the container
COPY flask_app.py /app/

# Expose the port the app runs on
EXPOSE 8080

# Set the Flask app to run when the container launches
CMD ["/venv/bin/python", "flask_app.py"]


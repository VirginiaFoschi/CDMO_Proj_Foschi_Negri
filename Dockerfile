# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to prevent pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for MiniZinc
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    libglib2.0-0 \
    libfontconfig1 \
    libfreetype6 \
    libgpg-error0 \
    libgcrypt20 \
    libgl1 \
    libegl1 \
    libglvnd0 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxi6 \
 && rm -rf /var/lib/apt/lists/*

# --- Install MiniZinc System Binary ---
# Adjust the version number here if you need a specific version
ENV MINIZINC_VERSION=2.9.1
ENV MINIZINC_ARCH=x86_64
RUN wget https://github.com/MiniZinc/MiniZincIDE/releases/download/${MINIZINC_VERSION}/MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH}.tgz \
    && tar xzf MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH}.tgz \
    && mv MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH} /opt/minizinc \
    && rm MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH}.tgz

# Add MiniZinc to PATH so Python can find it
ENV PATH="/opt/minizinc/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/minizinc/lib:${LD_LIBRARY_PATH}"

RUN minizinc --version && minizinc --solvers

# --- Setup Project ---
# Set the working directory in the container
WORKDIR /app

# Copy the dependency file first (better for Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . /app

# Define the entry point to your automation script
CMD ["python", "source/CP/run.py"]
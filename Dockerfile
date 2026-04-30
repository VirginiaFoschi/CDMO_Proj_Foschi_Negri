# Use an official Python runtime as a parent image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    gcc \
    g++ \
    make \
    libffi-dev \
    coinor-cbc \
    libgl1 \
    libegl1 \
    libfontconfig1 \
    libfreetype6 \
    libgpg-error0 \
 && rm -rf /var/lib/apt/lists/*

# --- Install MiniZinc System Binary ---
ENV MINIZINC_VERSION=2.9.1
ENV MINIZINC_ARCH=x86_64
RUN wget https://github.com/MiniZinc/MiniZincIDE/releases/download/${MINIZINC_VERSION}/MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH}.tgz \
    && tar xzf MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH}.tgz \
    && mv MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH} /opt/minizinc \
    && rm MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-${MINIZINC_ARCH}.tgz

ENV PATH="/opt/minizinc/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/minizinc/lib"

RUN minizinc --version && minizinc --solvers

# --- Setup Project ---
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Smoke-test: SAT solvers
RUN python -c "\
from pysat.solvers import Solver; \
[Solver(name=s).delete() for s in ['glucose3','glucose4','minisat22','cadical195','maplesat','mergesat3']]; \
print('All SAT solvers OK')"

# Smoke-test: MIP solvers (HiGHS + CBC)
RUN python -c "import highspy; print('HiGHS OK')" && \
    cbc -quit && echo "CBC OK"

COPY . /app

CMD ["python", "source/CP/run.py"]

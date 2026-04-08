FROM continuumio/miniconda3:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install rdkit via conda-forge + pip packages
RUN conda install -y -c conda-forge python=3.11 rdkit=2023.09 \
    && conda clean -afy

COPY requirements-fe.txt .
RUN pip install --no-cache-dir -r requirements-fe.txt

# AWS CLI v2
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip \
    && curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip -q awscliv2.zip && ./aws/install && rm -rf awscliv2.zip aws \
    && apt-get purge -y curl unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY . /workspace/nextflow/

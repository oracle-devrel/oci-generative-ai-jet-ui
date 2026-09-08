FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    OLLAMA_HOST=http://localhost:11434 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gnupg \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Install NVIDIA Container Toolkit repo (for drivers verification inside container if needed)
# Note: Actual driver usage depends on the host and --gpus flag
RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
       sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
       tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama and pull default model
RUN ollama serve & \
    sleep 5 && \
    ollama pull gemma3:270m

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 7860
EXPOSE 11434

# Create a startup script
RUN echo '#!/bin/bash\n\
# Start Ollama in background\n\
ollama serve & \n\
\n\
echo "Waiting for Ollama to be ready..."\n\
until curl -s http://localhost:11434/api/tags >/dev/null; do\n\
    sleep 2\n\
done\n\
echo "Ollama is ready."\n\
\n\
echo "Pulling model..."\n\
ollama pull gemma3:270m\n\
\n\
echo "Starting Gradio application..."\n\
python gradio_app.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set entrypoint
ENTRYPOINT ["/app/start.sh"]

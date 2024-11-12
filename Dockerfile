FROM python:3.9

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RUST_MIN_STACK=4194304
ENV FOUNDRY_PROFILE=zksync
ENV FOUNDRY_DEBUG=1
ENV PATH="/root/.cargo/bin:/root/.foundry/bin:/root/.foundry-zksync/bin:/root/.zksolc/bin:${PATH}"


# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for foundry)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . "$HOME/.cargo/env"

# Install regular Foundry first
RUN curl -L https://foundry.paradigm.xyz | bash && \
    /bin/bash -c "source /root/.bashrc && foundryup"

# Install zksolc compiler
RUN mkdir -p /root/.zksolc/bin && \
    wget https://github.com/matter-labs/zksolc-bin/raw/main/linux-amd64/zksolc-linux-amd64-musl-v1.5.4 -O /root/.zksolc/bin/zksolc && \
    chmod +x /root/.zksolc/bin/zksolc && \
    echo 'export PATH="/root/.zksolc/bin:$PATH"' >> /root/.bashrc && \
    ln -s /root/.zksolc/bin/zksolc /usr/local/bin/zksolc

# Install foundry-zksync
RUN curl -L https://raw.githubusercontent.com/matter-labs/foundry-zksync/main/foundryup-zksync/install | bash && \
    echo 'export PATH="/root/.foundry-zksync/bin:$PATH"' >> /root/.bashrc && \
    /bin/bash -c "source /root/.bashrc && foundryup-zksync"

# Verify installations
RUN /bin/bash -c "source /root/.bashrc && zksolc --version"
RUN /bin/bash -c "source /root/.bashrc && forge --version"
RUN forge build --help | grep -A 20 "ZKSync configuration:"

ENV FOUNDRY_PROFILE=zksync
ENV FOUNDRY_DEBUG=1

# Set up Django app
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip
RUN pip install -r requirements.txt
RUN python -m pip install --no-cache-dir pylibmc

# Copy application
COPY . .

# Create default port
ENV PORT=8000

# Start script
RUN echo '#!/bin/bash \
if [ -f .env ]; then \
    export $(cat .env | xargs) \
fi \
python manage.py migrate \
python manage.py collectstatic --noinput \
gunicorn base.asgi:application -b 0.0.0.0:$PORT -c gunicorn.conf.py' > /app/start.sh && \
chmod +x /app/start.sh

CMD ["/app/start.sh"]
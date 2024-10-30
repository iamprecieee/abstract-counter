FROM python:3.9

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RUST_MIN_STACK=4194304

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for foundry)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . "$HOME/.cargo/env"
ENV PATH="/root/.cargo/bin:${PATH}"

# Install regular Foundry first
RUN curl -L https://foundry.paradigm.xyz | bash && \
    /bin/bash -c "source /root/.bashrc && foundryup"

ENV PATH="/root/.foundry/bin:${PATH}"

# Install foundry-zksync with proper error handling
WORKDIR /tmp
RUN curl -L https://raw.githubusercontent.com/matter-labs/foundry-zksync/main/foundryup-zksync/install | bash && \
    echo 'export PATH="/root/.foundry-zksync/bin:$PATH"' >> /root/.bashrc && \
    /bin/bash -c "source /root/.bashrc && foundryup-zksync"

ENV PATH="/root/.foundry-zksync/bin:${PATH}"

# Verify installations
RUN forge --version
RUN forge build --help | grep -A 20 "ZKSync configuration:"


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
RUN echo '#!/bin/bash\n\
python manage.py migrate\n\
python manage.py collectstatic --noinput\n\
gunicorn base.asgi:application -b 0.0.0.0:$PORT -c gunicorn.conf.py' > /app/start.sh && \
chmod +x /app/start.sh

CMD ["/app/start.sh"]
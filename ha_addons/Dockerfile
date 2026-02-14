ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and build dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Note: --break-system-packages is required for Alpine 3.19+ (PEP 668)
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application files
COPY run.sh .
COPY src/ ./src/

# Make run script executable
RUN chmod a+x run.sh
# Version: 0.6.0 - Added standard SSE transport for MCP client compatibility
# Run the application
CMD [ "/app/run.sh" ]

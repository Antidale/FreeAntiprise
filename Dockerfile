FROM python:3.10-slim as base

WORKDIR /app

# System deps for compiling Floating IPS
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy local source (ie: whatever branch you have synched locally)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY ff4.rom.smc /app/ff4.rom.smc

FROM base as site
COPY f4c ./f4c/
COPY FreeEnt ./FreeEnt/
COPY .env .

# Build Floating IPS (headless) and place it where FreeEnt expects it
RUN wget -q https://github.com/Alcaro/Flips/archive/refs/heads/master.tar.gz -O flips.tar.gz && \
    tar xf flips.tar.gz && \
    cd Flips-master && \
    TARGET=cli make && \
    mkdir -p /app/FreeEnt/server/bin && \
    cp flips /app/FreeEnt/server/bin/flips-linux && \
    chmod +x /app/FreeEnt/server/bin/flips-linux && \
    cd .. && rm -rf Flips-master flips.tar.gz

# Fix CRLF line endings from Windows checkout before running shell scripts
RUN find /app -name "*.sh" -exec sed -i 's/\r$//' {} +

# Compile the randomizer spec files (required before server can run)
RUN cd /app/FreeEnt && bash compile_all_specs.sh

EXPOSE 8080
CMD ["python", "-m", "FreeEnt", "./ff4.rom.smc", "server", "--local"]

## Eventually, get the tools site running and accesible as well
FROM base AS tools
COPY fetools ./fetools
COPY f4c ./f4c
# Set up fe.pth so `python -m FreeEnt` can find the module
RUN echo "/app" > $(python -c "import site; print(site.getsitepackages()[0])")/fe.pth
EXPOSE 8082
CMD ["python", "./fetools/tool_site.py", "./ff4.rom.smc"]

FROM python:3.11-slim

# Install PlatformIO and dependencies
RUN pip install platformio

# Copy PlatformIO configuration
WORKDIR /app
COPY platformio.ini .
COPY src/ ./src/
COPY include/ ./include/
COPY test/ ./test/
COPY .clang-format .
COPY .gitignore .

# Default command - build the firmware
CMD ["platformio", "run"]

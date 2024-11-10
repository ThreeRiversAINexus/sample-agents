FROM python:3.11

WORKDIR /app

# Install system dependencies including ffmpeg for pydub
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
 COPY requirements.txt requirements.txt
# COPY main.py main.py
# COPY ds/ ds/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Define the directory that can be mounted from the host
VOLUME ["/app"]

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]

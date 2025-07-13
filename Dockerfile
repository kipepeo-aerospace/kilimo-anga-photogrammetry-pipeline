# lightweight Python base image
FROM python:3.10-slim


# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    libexpat1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app


# Copy only requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .


# Set default command (no hardcoded input/output paths)
CMD ["python", "main.py"]

#CMD ["python", "main.py", "--input_dir", "test_images", "--output_dir", "results", "--index", "VARI"]

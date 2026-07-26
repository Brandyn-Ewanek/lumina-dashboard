# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Upgrade pip and install the required dependencies
RUN pip install --no-cache-dir pandas yfinance boto3

# Copy the Python script into the container
COPY data_collection.py .

# Command to run when the container starts
CMD ["python", "data_collection.py"]

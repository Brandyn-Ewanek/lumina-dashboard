# STREAMING_CHUNK:Setting up the Python environment...

# Use a lightweight Python base image to keep AWS costs and boot times low

FROM python:3.11-slim

# Set the working directory in the container

WORKDIR /app

# STREAMING_CHUNK:Installing required libraries...

#Install the necessary dependencies, specifically edgartools for the SEC EDGAR database

RUN pip install --no-cache-dir pandas boto3 edgartools "hishel<0.1.0"

#STREAMING_CHUNK:Copying the script...

#Copy your insider script into the container

COPY insider_data_collector.py .

# STREAMING_CHUNK:Setting the start command...

#Command to run when the Fargate task wakes up

CMD ["python", "insider_data_collector.py"]
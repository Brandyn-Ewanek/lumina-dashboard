FROM python:3.9-slim

WORKDIR /app

RUN pip install --no-cache-dir pandas boto3

COPY macro_data_collection.py .

CMD ["python", "macro_data_collection.py"]
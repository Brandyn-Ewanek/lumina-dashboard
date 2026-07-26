import json
import boto3
import os

def lambda_handler(event, context):
    try:
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        s3 = boto3.client('s3')
        
        # Parse the JSON data sent from React
        body = json.loads(event.get('body', '{}'))
        favorites_array = body.get('favorites', [])
        
        # Save it directly to S3
        s3.put_object(
            Bucket=bucket_name,
            Key='dashboard/favorites/macro_favorites.json',
            Body=json.dumps(favorites_array),
            ContentType='application/json'
        )
        
        # We don't need to return CORS headers here anymore, 
        # because your AWS UI is doing it for us!
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "success"})
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
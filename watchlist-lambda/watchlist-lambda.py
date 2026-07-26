import json
import boto3
import os

def lambda_handler(event, context):
    try:
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        s3 = boto3.client('s3')
        
        # 1. Parse the incoming Watchlist from the React Dashboard
        body = json.loads(event.get('body', '{}'))
        watchlist_array = body.get('watchlist', [])
        
        # 2. Save it directly to the S3 folder
        s3.put_object(
            Bucket=bucket_name,
            Key='dashboard/watchlist/watchlist.json',
            Body=json.dumps(watchlist_array),
            ContentType='application/json'
        )
        
        # 3. Return success (No manual CORS headers needed here!)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"status": "success", "saved_count": len(watchlist_array)})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
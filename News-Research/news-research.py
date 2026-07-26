import urllib.request
import urllib.error
import json
import os
import boto3
from datetime import datetime

def lambda_handler(event, context):
    # 1. Handle browser pre-flight checks manually
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {"statusCode": 200, "headers": headers, "body": ""}

    try:
        # 2. Parse the target Ticker from React
        body = json.loads(event.get('body', '{}'))
        ticker = body.get('ticker')
        if not ticker:
            raise ValueError("No ticker provided in request body!")

        bucket_name = os.environ.get('S3_BUCKET_NAME')
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        # Explicitly check for missing environment variables!
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is missing in AWS!")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing in AWS!")

        s3 = boto3.client('s3')

        # 3. Fetch the previous baseline report from S3 (if it exists)
        existing_report_text = "No previous baseline exists. This is the first analysis."
        file_key = f'dashboard/research/{ticker}_latest.json'
        try:
            response = s3.get_object(Bucket=bucket_name, Key=file_key)
            existing_report_text = response['Body'].read().decode('utf-8')
        except Exception:
            pass # No file exists yet, perfectly fine!

        # 4. Prompt Gemini to act as a financial analyst and evaluate the delta
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
        
        date_str = datetime.now().strftime("%B %d, %Y")
        prompt = f"""
        You are an expert institutional quantitative financial analyst. 
        We are generating an updated research memo for the stock ticker: {ticker}.
        Today's Date: {date_str}.

        PREVIOUS BASELINE REPORT FOR CONTEXT:
        {existing_report_text}

        TASK: Analyze {ticker}'s current market position, recent headlines, and overall trajectory. 
        Identify if recent price action is a "Permanent Failure" or a "Temporary Overreaction".
        If a baseline report was provided above, strictly focus on the DELTA (what has changed since that report).

        Respond STRICTLY with a valid JSON object matching this exact format (no markdown, no backticks, just raw JSON):
        {{
          "ticker": "{ticker}",
          "lastBaseline": "{date_str}",
          "verdict": "Temporary Overreaction", 
          "confidence": 85,
          "thesisShift": "Neutral to Temporary Overreaction based on...",
          "deltaMatrix": [
            {{
              "baseline": "Expected 12% revenue growth...",
              "current": "Q2 revenue guidance cut by 4%...",
              "assessment": "Core volume demand remains strong...",
              "type": "Temporary"
            }}
          ],
          "structuralRisks": [
            "New competitive threats emerging."
          ],
          "transitoryFactors": [
            "Recent earnings miss driven by one-time setup costs."
          ],
          "timeline": [
            {{ "date": "Recent", "event": "Earnings miss causes dip.", "impact": "Negative" }}
          ]
        }}
        """

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        req = urllib.request.Request(gemini_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        # 5. Connect to Google with Hardened Error Catching
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            # If Google rejects it, capture the exact reason why!
            error_body = e.read().decode('utf-8')
            raise ValueError(f"Google Gemini rejected the request: {error_body}")
            
        ai_response = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean the response to ensure it is raw JSON
        ai_response = ai_response.replace('```json', '').replace('```', '').strip()
        report_json = json.loads(ai_response)

        # 6. Save the brand new report back to S3, overwriting the old baseline!
        s3.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=json.dumps(report_json, indent=4),
            ContentType='application/json'
        )

        # 7. Send the report back to the React Dashboard
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(report_json)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }
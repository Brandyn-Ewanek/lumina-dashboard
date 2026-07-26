import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import boto3

def lambda_handler(event, context):
    print("Waking up AI Sentiment Engine...")
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    gemini_key = os.environ.get('GEMINI_API_KEY')
    
    if not bucket_name or not gemini_key:
        return {"statusCode": 500, "body": "Missing Environment Variables!"}

    try:
        # 1. Scrape the latest Top Market Headlines from CNBC RSS
        print("Fetching latest headlines from CNBC...")
        rss_url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        # Extract the top 15 headlines
        headlines = [item.find('title').text for item in root.findall('.//item')][:15]
        headlines_text = "\n- ".join(headlines)
        
        print(f"Found {len(headlines)} headlines.")

        # 2. Ask Google Gemini to analyze the sentiment
        print("Sending to Google Gemini for analysis...")
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
        
        prompt = f"""
        You are an expert quantitative financial analyst. 
        Read the following recent market headlines and determine the overall market sentiment.
        
        Headlines:
        - {headlines_text}
        
        Respond STRICTLY with a valid JSON object matching this exact format, with no markdown formatting or extra text:
        {{
            "sentiment": "Bullish" (or "Bearish" or "Neutral"),
            "confidence": 85 (a number between 0 and 100 representing your confidence in this assessment),
            "summary": "Tech rallies on earnings" (A strict 3 to 5 word summary of the overall theme)
        }}
        """
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        req = urllib.request.Request(gemini_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        # Extract Gemini's text response
        ai_response = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean up any potential markdown formatting from the AI
        ai_response = ai_response.replace('```json', '').replace('```', '').strip()
        sentiment_json = json.loads(ai_response)
        
        # Add our article count for the dashboard to display
        sentiment_json['articleCount'] = len(headlines)
        
        print(f"Analysis Complete: {sentiment_json}")

        # 3. Retrieve History and Upload to S3
        print("Fetching existing history and uploading to S3...")
        s3 = boto3.client('s3')
        
        from datetime import datetime
        sentiment_json['date'] = datetime.now().strftime("%Y-%m-%d")
        
        existing_history = []
        try:
            # Try to grab the existing file
            response = s3.get_object(Bucket=bucket_name, Key='dashboard/sentiment/sentiment.json')
            existing_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Convert to array if it's the old single-object format
            if isinstance(existing_data, list):
                existing_history = existing_data
            else:
                existing_history = [existing_data]
        except Exception as e:
            print("No existing sentiment history found. Starting fresh.")

        # Append today's data and keep only the last 30 days
        existing_history.append(sentiment_json)
        existing_history = existing_history[-30:]
        
        s3.put_object(
            Bucket=bucket_name,
            Key='dashboard/sentiment/sentiment.json',
            Body=json.dumps(existing_history, indent=4),
            ContentType='application/json'
        )
        
        print("Upload successful!")
        return {"statusCode": 200, "body": "Sentiment generated and uploaded to S3 successfully!"}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": str(e)}
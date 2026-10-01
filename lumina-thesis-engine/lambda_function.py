import json
import boto3
import os
from datetime import datetime
from google import genai

s3 = boto3.client('s3')
BUCKET_NAME = 'lumina-strategies'

# Target the specific 'data/' path from your screenshot
ACTIVE_THEORIES_KEY = 'data/theories/active.json'

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def lambda_handler(event, context):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    method = event.get('requestContext', {}).get('http', {}).get('method')
    if method == 'OPTIONS':
        return {"statusCode": 200, "headers": headers, "body": ""}

    raw_path = event.get('rawPath', '/')
    
    try:
        body = json.loads(event.get('body', '{}'))

        # ROUTE 1: POLISH THESIS (AI SYNTHESIS)
        if raw_path == '/polish_thesis':
            prompt = f"""
            You are an institutional portfolio manager. Synthesize the user's raw notes into a rigorous, two-paragraph quantitative thesis.
            Inputs:
            - Ticker: {body.get('ticker')} | Entry Price: {body.get('entry_price')} | Target: {body.get('target_price')} | Horizon: {body.get('horizon')} days
            - Fundamentals: Fwd P/E {body.get('fwd_pe')}, D/E {body.get('de')}, Lumina Score {body.get('lumina_score')}
            - Live Catalyst / News: {body.get('catalyst_news')}
            - User Raw Input: {body.get('raw_notes')}

            Requirements:
            - Paragraph 1: State the core pricing inefficiency and macro/operational catalyst.
            - Paragraph 2: Highlight the downside defense and defined target outcome.
            """
            
            response = client.models.generate_content(
                model='gemini-1.5-pro',
                contents=prompt
            )
            
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"polished_thesis": response.text})
            }

        # ROUTE 2: COMMIT BUY (S3 STATE INGESTION)
        elif raw_path == '/commit_buy':
            entry_price = float(body.get('entry_price'))
            target_budget = 10000
            shares = int(target_budget // entry_price)
            
            new_theory = {
                "thesis_id": f"thm_{body.get('ticker').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "ticker": body.get('ticker'),
                "status": "OPEN",
                "allocation": {
                    "target_budget": target_budget,
                    "shares": shares,
                    "entry_price": entry_price,
                    "invested_capital": round(shares * entry_price, 2),
                    "exit_price": None,
                    "realized_pnl_dollars": None
                },
                "timeline": {
                    "entry_date": datetime.now().strftime('%Y-%m-%d'),
                    "target_date": body.get('target_date'),
                    "days_horizon": body.get('horizon_days')
                },
                "targets": {
                    "target_price": float(body.get('target_price')),
                },
                "thesis_narrative": {
                    "user_raw_notes": body.get('raw_notes'),
                    "gemini_institutional_thesis": body.get('polished_thesis')
                },
                "entry_snapshot": body.get('entry_snapshot', {})
            }

            response = s3.get_object(Bucket=BUCKET_NAME, Key=ACTIVE_THEORIES_KEY)
            active_theories = json.loads(response['Body'].read().decode('utf-8'))
            
            active_theories.append(new_theory)
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=ACTIVE_THEORIES_KEY,
                Body=json.dumps(active_theories, indent=2),
                ContentType='application/json'
            )

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"message": "Theory committed successfully", "theory": new_theory})
            }

        else:
            return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Route not found"})}

    except Exception as e:
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
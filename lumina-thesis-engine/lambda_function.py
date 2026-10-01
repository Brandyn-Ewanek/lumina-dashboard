import json
import boto3
import os
from datetime import datetime
from google import genai

s3 = boto3.client('s3')
BUCKET_NAME = 'lumina-strategies'
ACTIVE_THEORIES_KEY = 'data/theories/active.json'

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def lambda_handler(event, context):
    
    raw_path = event.get('rawPath', '/')

    try:
        # Safely parse the body
        body_str = event.get('body') or '{}'
        body = json.loads(body_str)

        # ROUTE 1: POLISH THESIS (AI SYNTHESIS)
        if 'polish_thesis' in raw_path:
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
                model='gemini-3.1-pro-preview',
                contents=prompt
            )
            
            return {
                "statusCode": 200,
                "body": json.dumps({"polished_thesis": response.text})
            }

        # ROUTE 2: COMMIT BUY (S3 STATE INGESTION)
        elif 'commit_buy' in raw_path:
            entry_price = float(body.get('entry_price', 1)) # Fallback to 1 to prevent division by zero
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
                    "target_price": float(body.get('target_price', 0)),
                },
                "thesis_narrative": {
                    "user_raw_notes": body.get('raw_notes'),
                    "gemini_institutional_thesis": body.get('polished_thesis')
                },
                "entry_snapshot": body.get('entry_snapshot', {})
            }

            # Try to fetch existing theories, or start a new list if file doesn't exist yet
            try:
                s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=ACTIVE_THEORIES_KEY)
                active_theories = json.loads(s3_response['Body'].read().decode('utf-8'))
            except Exception:
                active_theories = []
            
            active_theories.append(new_theory)
            
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=ACTIVE_THEORIES_KEY,
                Body=json.dumps(active_theories, indent=2),
                ContentType='application/json'
            )

            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Buy committed to S3 successfully", "thesis_id": new_theory["thesis_id"]})
            }

    except Exception as e:
        # Catch any AI or JSON errors cleanly (NO headers referenced here)
        return {
            "statusCode": 500, 
            "body": json.dumps({"error": str(e)})
        }

    # If the URL path doesn't match 'polish_thesis' or 'commit_buy', return a 404
    return {
        "statusCode": 404, 
        "body": json.dumps({"error": f"Route not found: {raw_path}"})
    }
import json
import boto3
import os
from datetime import datetime
from google import genai

s3 = boto3.client('s3')
BUCKET_NAME = 'lumina-strategies'
ACTIVE_THEORIES_KEY = 'data/theories/active.json'
HISTORY_THEORIES_KEY = 'data/theories/history.json' # NEW HISTORY FILE

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def lambda_handler(event, context):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }

    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {"statusCode": 200, "headers": headers, "body": ""}

    try:
        body_str = event.get('body') or '{}'
        body = json.loads(body_str)
        action = body.get('action')

        # ROUTE 1: POLISH THESIS
        if action == 'polish':
            prompt = f"""
            You are an institutional portfolio manager. Synthesize the user's raw notes into a highly concise, bullet-point quantitative thesis.
            Inputs:
            - Ticker: {body.get('ticker')} | Entry Price: {body.get('entry_price')} | Target: {body.get('target_price')} | Horizon: {body.get('horizon')} days
            - Fundamentals: Fwd P/E {body.get('fwd_pe')}, D/E {body.get('de')}, Lumina Score {body.get('lumina_score')}
            - Live Catalyst / News: {body.get('catalyst_news')}
            - User Raw Input: {body.get('raw_notes')}

            Requirements:
            - Output strictly in concise, punchy bullet points. Do not use filler paragraphs.
            - Section 1: Core Inefficiency & Catalyst (Max 3 bullets)
            - Section 2: Downside Defense & Target (Max 3 bullets)
            """
            
            response = client.models.generate_content(
                model='gemini-3.1-pro-preview',
                contents=prompt
            )
            
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"polished_thesis": response.text})}

        # ROUTE 2: COMMIT BUY
        elif action == 'commit':
            entry_price = float(body.get('entry_price', 1))
            target_budget = float(body.get('target_budget', 10000)) 
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

            try:
                s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=ACTIVE_THEORIES_KEY)
                active_theories = json.loads(s3_response['Body'].read().decode('utf-8'))
            except Exception:
                active_theories = []
            
            active_theories.append(new_theory)
            
            s3.put_object(Bucket=BUCKET_NAME, Key=ACTIVE_THEORIES_KEY, Body=json.dumps(active_theories, indent=2), ContentType='application/json')
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Buy committed to S3 successfully"})}

        # ROUTE 3: CLOSE TRADE (THE SELL ENGINE)
        elif action == 'close_trade':
            thesis_id = body.get('thesis_id')
            exit_price = float(body.get('exit_price', 0))
            
            # Fetch active theories
            try:
                s3_active = s3.get_object(Bucket=BUCKET_NAME, Key=ACTIVE_THEORIES_KEY)
                active_theories = json.loads(s3_active['Body'].read().decode('utf-8'))
            except Exception:
                active_theories = []
                
            trade_to_close = None
            remaining_theses = []
            
            for t in active_theories:
                if t.get('thesis_id') == thesis_id:
                    trade_to_close = t
                else:
                    remaining_theses.append(t)
                    
            if not trade_to_close:
                return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Thesis ID not found."})}
                
            # Update the closed trade payload
            trade_to_close['status'] = 'CLOSED'
            trade_to_close['timeline']['exit_date'] = datetime.now().strftime('%Y-%m-%d')
            trade_to_close['allocation']['exit_price'] = exit_price
            
            invested = trade_to_close['allocation']['invested_capital']
            shares = trade_to_close['allocation']['shares']
            trade_to_close['allocation']['realized_pnl_dollars'] = round((shares * exit_price) - invested, 2)
            
            # Save the market conditions exactly as they are on the day of the sale
            trade_to_close['exit_snapshot'] = body.get('exit_snapshot', {})
            
            # 1. Overwrite active.json without the closed trade
            s3.put_object(Bucket=BUCKET_NAME, Key=ACTIVE_THEORIES_KEY, Body=json.dumps(remaining_theses, indent=2), ContentType='application/json')
            
            # 2. Append the closed trade to history.json
            try:
                s3_history = s3.get_object(Bucket=BUCKET_NAME, Key=HISTORY_THEORIES_KEY)
                history_theories = json.loads(s3_history['Body'].read().decode('utf-8'))
            except Exception:
                history_theories = []
                
            history_theories.append(trade_to_close)
            s3.put_object(Bucket=BUCKET_NAME, Key=HISTORY_THEORIES_KEY, Body=json.dumps(history_theories, indent=2), ContentType='application/json')
            
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Trade moved to Post-Mortem history"})}

        else:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "No valid action provided."})}

    except Exception as e:
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
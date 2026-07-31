import json
import os
import boto3
import pandas as pd
import time
from io import StringIO
from datetime import datetime, timedelta
from edgar import set_identity, Company

def calculate_conviction_score(transactions):
    score = 0
    buy_count = 0
    total_buy_value = 0
    
    for t in transactions:
        # We want ALL buys so we can see the historical trend over time.
        if t['type'] == 'BUY':
            buy_count += 1
            total_buy_value += t['total_value']
                
    if buy_count == 0:
        return 0
        
    score += min(50, buy_count * 5)
        
    if total_buy_value > 1000000:
        score += 50
    elif total_buy_value > 250000:
        score += 25
    elif total_buy_value > 50000:
        score += 10
        
    return min(100, score)

def get_insider_trades(ticker, start_date):
    try:
        set_identity("Lumina Strategies Quantitative Engine (your.email@example.com)")
        company = Company(ticker)
        if not company:
            return []

        filings = company.get_filings(form="4").filter(date=f"{start_date}:")
        parsed_transactions = []
        error_printed = False 
        
        for filing in filings:
            try:
                form4 = filing.obj()
                
                # BULLETPROOFING: Safely handle different versions of the edgartools library
                if hasattr(form4, 'get_ownership_summary'):
                    # Newest edgartools version
                    summary = form4.get_ownership_summary()
                    insider_name = getattr(summary, 'insider_name', 'Unknown')
                    title = getattr(summary, 'position', 'Director/Officer')
                    trades = getattr(summary, 'transactions', [])
                else:
                    # Older edgartools version
                    insider_name = getattr(form4, 'reporting_owner_name', 'Unknown')
                    title = getattr(form4, 'reporting_owner_relationship', 'Director/Officer')
                    trades = getattr(form4, 'transactions', getattr(form4, 'non_derivatives', []))
                    if not isinstance(trades, list) and hasattr(trades, 'trades'):
                        trades = trades.trades
                
                for trade in trades:
                    # Safely extract the code ('P' for Purchase, 'S' for Sale)
                    code = getattr(trade, 'code', getattr(trade, 'transaction_code', ''))
                    if code not in ['P', 'S']:
                        continue
                        
                    trade_type = "BUY" if code == 'P' else "SELL"
                    
                    # Safely extract shares and prices
                    shares = getattr(trade, 'shares_numeric', getattr(trade, 'shares', 0))
                    price = getattr(trade, 'price_numeric', getattr(trade, 'price_per_share', getattr(trade, 'price', 0)))
                    
                    shares = float(shares) if shares else 0
                    price = float(price) if price else 0
                    total_value = shares * price
                    
                    # Safely check footnotes for 10b5-1 automated plans
                    footnotes = getattr(trade, 'footnotes', '')
                    is_automated = "10b5-1" in str(footnotes).lower()
                    
                    parsed_transactions.append({
                        "date": str(filing.filing_date),
                        "insider_name": insider_name,
                        "title": title,
                        "type": trade_type,
                        "shares": shares,
                        "price": price,
                        "total_value": total_value,
                        "is_10b5_1": is_automated
                    })
            except Exception as e:
                if not error_printed:
                    print(f"Data extraction error on {ticker} Form 4: {str(e)}", flush=True)
                    error_printed = True
                continue
                
        return parsed_transactions
    except Exception as e:
        print(f"SEC Blocked/Error on {ticker}: {str(e)}", flush=True)
        return []

def get_oldest_stock_date(s3_client, bucket_name):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key='data/today/sp500_latest.csv')
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(csv_content), low_memory=False)
        if 'Date' in df.columns:
            return df['Date'].min()
    except Exception as e:
        print(f"Could not find oldest date, using fallback: {e}", flush=True)
    return (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")

def get_all_tracked_tickers(s3_client, bucket_name):
    tickers = set()
    indices = ['sp500', 'sp400', 'sp600']
    
    print("Fetching master ticker list from S3 data lake...", flush=True)
    for index in indices:
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=f'data/today/{index}_latest.csv')
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_content), low_memory=False)
            if 'Ticker' in df.columns:
                tickers.update(df['Ticker'].dropna().unique().tolist())
        except Exception as e:
            print(f"Warning: Could not load tickers for {index}: {e}", flush=True)
            
    if not tickers:
        return ["AAPL", "MSFT", "WDFC", "CELH"]
        
    master_list = sorted(list(tickers))
    print(f"Successfully compiled {len(master_list)} unique tickers for SEC scanning.", flush=True)
    return master_list

def main():
    print("Waking up Full-Market SEC Insider Data Collector v6...", flush=True)
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    s3_client = boto3.client('s3')
    
    start_date = get_oldest_stock_date(s3_client, bucket_name) if bucket_name else "2023-01-01"
    print(f"Aligning insider trades back to earliest price record: {start_date}", flush=True)
    
    tickers = get_all_tracked_tickers(s3_client, bucket_name)
    
    all_opportunities = []
    processed_count = 0

    for ticker in tickers:
        try:
            time.sleep(0.15)
            
            processed_count += 1
            if processed_count % 50 == 0:
                print(f"Progress: Scanned {processed_count}/{len(tickers)} companies...", flush=True)
                
            transactions = get_insider_trades(ticker, start_date=start_date)
            
            if transactions:
                conviction_score = calculate_conviction_score(transactions)
                summary_object = {
                    "ticker": ticker,
                    "conviction_score": conviction_score,
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "insider_transactions": transactions
                }
                
                # Adding ALL valid findings to our master list
                all_opportunities.append(summary_object)
                
                file_key = f"dashboard/insider_trading/{ticker}_insiders.json"
                if bucket_name:
                    s3_client.put_object(
                        Bucket=bucket_name, Key=file_key,
                        Body=json.dumps(summary_object, indent=4), ContentType='application/json'
                    )
        except Exception as e:
            print(f"Warning: Failed processing {ticker} due to error: {e}", flush=True)
            continue

    all_opportunities.sort(key=lambda x: x['conviction_score'], reverse=True)
    
    if bucket_name and all_opportunities:
        s3_client.put_object(
            Bucket=bucket_name, Key="dashboard/insider_trading/ranked_opportunities.json",
            Body=json.dumps(all_opportunities, indent=4), ContentType='application/json'
        )
        print(f"Successfully uploaded all {len(all_opportunities)} Insider Records to S3.", flush=True)
    else:
        print(f"Finished script. Processed {len(tickers)} tickers. However, found ZERO transactions. Upload skipped.", flush=True)

if __name__ == "__main__":
    main()
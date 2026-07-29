import json
import os
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from edgar import set_identity, Company

def calculate_conviction_score(transactions):
    """
    A basic algorithmic scoring engine to rank opportunities.
    Higher volume purchases by C-suite executives generate higher scores.
    """
    score = 0
    buy_count = 0
    total_buy_value = 0
    
    for t in transactions:
        if t['type'] == 'BUY' and not t['is_10b5_1']:
            buy_count += 1
            total_buy_value += t['total_value']
            
            # C-Suite gets higher weighting than general board members
            if any(role in t['title'].upper() for role in ['CEO', 'CFO', 'PRESIDENT', 'CHIEF']):
                score += 25
            else:
                score += 10
                
    # Weight based on total dollar value of open-market buys
    if total_buy_value > 1000000:
        score += 50
    elif total_buy_value > 250000:
        score += 25
    elif total_buy_value > 50000:
        score += 10
        
    # Cap score at 100
    return min(100, score)

def get_insider_trades(ticker, start_date):
    """
    Queries the SEC EDGAR database for Form 4 (Insider Trading) filings.
    """
    try:
        # SEC requires you to identify your script to prevent IP bans
        set_identity("Lumina Strategies Quantitative Engine (your.email@example.com)")
        
        company = Company(ticker)
        if not company:
            return []

        # Fetch only Form 4 filings from the dynamic start_date forward
        filings = company.get_filings(form="4").filter(date=f">={start_date}")
        
        parsed_transactions = []
        
        for filing in filings:
            try:
                # edgartools automatically parses the messy SEC XML into a Python object
                form4 = filing.obj()
                
                # Get reporting owner details
                insider_name = form4.reporting_owner.name
                title = form4.reporting_owner.title or "Director/Officer"
                
                # Loop through the non-derivative transactions (actual stock buys/sells)
                for trade in form4.non_derivatives.trades:
                    # 'A' means Acquired (Buy), 'D' means Disposed (Sell)
                    trade_type = "BUY" if trade.acquired_disposed == 'A' else "SELL"
                    
                    # We are only interested in open market transactions, not stock grants
                    if trade.transaction_code not in ['P', 'S']: # P = Purchase, S = Sale
                        continue
                        
                    shares = float(trade.shares) if trade.shares else 0
                    price = float(trade.price) if trade.price else 0
                    total_value = shares * price
                    
                    # Look for 10b5-1 automated trading plans in the footnotes
                    is_automated = "10b5-1" in str(trade.footnotes).lower()
                    
                    parsed_transactions.append({
                        "date": filing.filing_date,
                        "insider_name": insider_name,
                        "title": title,
                        "type": trade_type,
                        "shares": shares,
                        "price": price,
                        "total_value": total_value,
                        "is_10b5_1": is_automated
                    })
            except Exception as e:
                # Skip individual filings that are formatted improperly by the SEC
                continue
                
        return parsed_transactions
    except Exception as e:
        # Suppress individual company lookup errors to keep logs clean during full-market scan
        return []

def get_oldest_stock_date(s3_client, bucket_name):
    """Fetches the oldest date from the existing S3 stock data."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key='data/today/sp500_latest.csv')
        csv_content = response['Body'].read().decode('utf-8')
        # Added low_memory=False to silence Pandas Dtype warnings
        df = pd.read_csv(StringIO(csv_content), low_memory=False)
        if 'Date' in df.columns:
            return df['Date'].min()
    except Exception as e:
        print(f"Could not find oldest date, using fallback: {e}")
    
    # Fallback to roughly 3 years ago if S3 read fails
    return (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")

def get_all_tracked_tickers(s3_client, bucket_name):
    """Dynamically builds a master list of all US equities tracked in your pipeline."""
    tickers = set()
    indices = ['sp500', 'sp400', 'sp600'] # Excluding TSX as EDGAR is US-centric
    
    print("Fetching master ticker list from S3 data lake...")
    for index in indices:
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=f'data/today/{index}_latest.csv')
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_content), low_memory=False)
            if 'Ticker' in df.columns:
                # Add all unique tickers to our set (automatically removes duplicates)
                tickers.update(df['Ticker'].dropna().unique().tolist())
        except Exception as e:
            print(f"Warning: Could not load tickers for {index}: {e}")
            
    # Fallback just in case S3 is completely empty
    if not tickers:
        print("Warning: No tickers found in S3. Falling back to test list.")
        return ["AAPL", "MSFT", "WDFC", "CELH"]
        
    master_list = sorted(list(tickers))
    print(f"Successfully compiled {len(master_list)} unique tickers for SEC scanning.")
    return master_list

def main():
    print("Waking up Full-Market SEC Insider Data Collector...")
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    s3_client = boto3.client('s3')
    
    # Determine the exact start date to match your price history
    start_date = get_oldest_stock_date(s3_client, bucket_name) if bucket_name else "2023-01-01"
    print(f"Aligning insider trades back to earliest price record: {start_date}")
    
    # Dynamically fetch the 1,500+ tracked tickers from your S3 buckets
    tickers = get_all_tracked_tickers(s3_client, bucket_name)
    
    all_summaries = []
    processed_count = 0

    for ticker in tickers:
        processed_count += 1
        if processed_count % 50 == 0:
            print(f"Progress: Scanned {processed_count}/{len(tickers)} companies...")
            
        transactions = get_insider_trades(ticker, start_date=start_date)
        
        if transactions:
            conviction_score = calculate_conviction_score(transactions)
            
            # Create the exact JSON contract your React Dashboard is expecting
            summary_object = {
                "ticker": ticker,
                "conviction_score": conviction_score,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "insider_transactions": transactions
            }
            all_summaries.append(summary_object)
            
            # Upload individual ticker JSON to S3
            file_key = f"dashboard/insider_trading/{ticker}_insiders.json"
            if bucket_name:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_key,
                    Body=json.dumps(summary_object, indent=4),
                    ContentType='application/json'
                )

    # Finally, sort by the highest conviction scores and save a "Top Opportunities" list
    all_summaries.sort(key=lambda x: x['conviction_score'], reverse=True)
    # Give the dashboard the top 30 highest conviction plays
    top_opportunities = [s for s in all_summaries if s['conviction_score'] > 0][:30]
    
    if bucket_name and top_opportunities:
        s3_client.put_object(
            Bucket=bucket_name,
            Key="dashboard/insider_trading/ranked_opportunities.json",
            Body=json.dumps(top_opportunities, indent=4),
            ContentType='application/json'
        )
        print("Successfully uploaded Top 30 Ranked Opportunities to S3.")

if __name__ == "__main__":
    main()
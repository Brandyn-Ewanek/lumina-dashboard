import json
import os
import boto3
import pandas as pd
from datetime import datetime, timedelta
# edgartools is the secret weapon for SEC scraping without APIs
from edgar import set_identity, Company, get_filings

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
        print(f"Failed to fetch EDGAR data for {ticker}: {e}")
        return []

def get_oldest_stock_date(s3_client, bucket_name):
    """Fetches the oldest date from the existing S3 stock data."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key='data/today/sp500_latest.csv')
        df = pd.read_csv(pd.compat.StringIO(response['Body'].read().decode('utf-8'))) if hasattr(pd, 'compat') else pd.read_csv(__import__('io').StringIO(response['Body'].read().decode('utf-8')))
        if 'Date' in df.columns:
            return df['Date'].min()
    except Exception as e:
        print(f"Could not find oldest date, using fallback: {e}")
    
    # Fallback to roughly 3 years ago if S3 read fails
    return (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")

def main():
    print("Waking up SEC Insider Data Collector...")
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    s3_client = boto3.client('s3')
    
    # Determine the exact start date to match your price history
    start_date = get_oldest_stock_date(s3_client, bucket_name) if bucket_name else "2023-01-01"
    print(f"Aligning insider trades back to earliest price record: {start_date}")
    
    # For testing, we will use a small sample of the S&P 600
    # In production, this loads your cached ticker lists from S3
    tickers = ["SMLR", "LANC", "WDFC", "RICK", "CELH"] 
    
    all_summaries = []

    for ticker in tickers:
        print(f"Scanning SEC filings for {ticker} since {start_date}...")
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
    # This powers the floating dock at the bottom of your UI!
    all_summaries.sort(key=lambda x: x['conviction_score'], reverse=True)
    top_opportunities = [s for s in all_summaries if s['conviction_score'] > 0][:20]
    
    if bucket_name and top_opportunities:
        s3_client.put_object(
            Bucket=bucket_name,
            Key="dashboard/insider_trading/ranked_opportunities.json",
            Body=json.dumps(top_opportunities, indent=4),
            ContentType='application/json'
        )
        print("Successfully uploaded Ranked Opportunities to S3.")

if __name__ == "__main__":
    main()
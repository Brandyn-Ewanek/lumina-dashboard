import pandas as pd
import yfinance as yf
import boto3
import json
import time
import os
from datetime import datetime
from io import StringIO

def get_sp500_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = table[0]
        tickers = df['Symbol'].tolist()
        # Yahoo Finance uses '-' instead of '.' for classes (e.g., BRK.B -> BRK-B)
        tickers = [str(ticker).replace('.', '-') for ticker in tickers]
        print(f"Successfully fetched {len(tickers)} live S&P 500 tickers from Wikipedia.")
        return tickers
    except Exception as e:
        print(f"Notice: Dynamic S&P 500 fetch failed ({e}).")
        return []

def get_sp400_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies')
        df = table[0]
        tickers = df['Symbol'].tolist()
        tickers = [str(ticker).replace('.', '-') for ticker in tickers]
        print(f"Successfully fetched {len(tickers)} live S&P 400 MidCap tickers from Wikipedia.")
        return tickers
    except Exception as e:
        print(f"Notice: Dynamic S&P 400 fetch failed ({e}).")
        return []

def get_sp600_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_600_companies')
        df = table[0]
        tickers = df['Symbol'].tolist()
        tickers = [str(ticker).replace('.', '-') for ticker in tickers]
        print(f"Successfully fetched {len(tickers)} live S&P 600 SmallCap tickers from Wikipedia.")
        return tickers
    except Exception as e:
        print(f"Notice: Dynamic S&P 600 fetch failed ({e}).")
        return []

def get_tsx_tickers():
    try:
        # The TSX table is usually the second table on the Wikipedia page
        tables = pd.read_html('https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index')
        df = tables[1]
        tickers = df['Symbol'].tolist()
        # Clean TSX tickers and append '.TO' for Yahoo Finance recognition
        tickers = [f"{str(ticker).replace('.', '-')}.TO" for ticker in tickers]
        print(f"Successfully fetched {len(tickers)} live TSX Composite tickers from Wikipedia.")
        return tickers
    except Exception as e:
        print(f"Notice: Dynamic TSX fetch failed ({e}).")
        return []

def get_cached_tickers(bucket_name, index_id, fresh_tickers):
    """
    Takes the freshly scraped Wikipedia tickers. If successful, saves them as a backup.
    If Wikipedia failed (returned empty list), loads the last known good backup from S3.
    """
    s3_client = boto3.client('s3')
    cache_key = f'data/ticker_lists/{index_id}_cached_tickers.csv'
    
    if fresh_tickers and len(fresh_tickers) > 0:
        try:
            # Save the successful fetch to S3 as a backup for tomorrow
            df = pd.DataFrame({'Ticker': fresh_tickers})
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3_client.put_object(Bucket=bucket_name, Key=cache_key, Body=csv_buffer.getvalue())
        except Exception as e:
            print(f"Notice: Could not save backup cache for {index_id} ({e}).")
        return fresh_tickers
    else:
        print(f"Warning: Live fetch for {index_id} failed. Attempting to load from S3 backup...")
        try:
            # Wikipedia failed, load the backup!
            response = s3_client.get_object(Bucket=bucket_name, Key=cache_key)
            existing_csv_string = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(existing_csv_string))
            fallback_tickers = df['Ticker'].tolist()
            print(f"Success! Loaded {len(fallback_tickers)} backup tickers for {index_id}.")
            return fallback_tickers
        except Exception as e:
            print(f"Critical: No backup cache found for {index_id} ({e}). Skipping.")
            return []

def get_yahoo_data(ticker):
    """
    Fetches the necessary financial metrics for a single ticker from Yahoo Finance.
    """
    try:
        stock = yf.Ticker(ticker)
        # Using fast_info for immediate market data where possible, falling back to info
        info = stock.info
        
        # Handle cases where the stock might be delisted but still in the index list temporarily
        if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info:
            raise ValueError("No valid pricing data found.")

        # Safely extract metrics with fallbacks
        close_price = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', None)))
        target_price = info.get('targetMeanPrice', None)
        
        pe_ratio = info.get('trailingPE', None)
        forward_pe = info.get('forwardPE', None)
        market_cap = info.get('marketCap', None)
        volume = info.get('volume', info.get('regularMarketVolume', None))
        avg_volume = info.get('averageVolume', None)
        
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')

        return {
            'Ticker': ticker,
            'Company_Name': info.get('shortName', ticker),
            'Close_Price': close_price,
            'Target_Mean_Price': target_price,
            'Trailing_PE': pe_ratio,
            'Forward_PE': forward_pe,
            'Market_Cap': market_cap,
            'Volume': volume,
            'Average_Volume': avg_volume,
            'Sector': sector,
            'Industry': industry
        }
    except Exception as e:
        return {'Ticker': ticker, 'Error': str(e)}

def upload_index_to_s3(today_df, error_dict, today_obj, bucket_name, index_id, index_display_name):
    """
    Downloads the master 'latest' file, appends today's data, drops duplicates, 
    uploads the updated master back to the dashboard folder, and saves a snapshot to the archive.
    """
    s3_client = boto3.client('s3')
    today_str = today_obj.strftime('%Y-%m-%d')
    
    # 1. Add Date column to today's data so we can track it over time
    if 'Date' not in today_df.columns:
        today_df.insert(0, 'Date', today_str)

    latest_key = f"data/today/{index_id}_latest.csv"
    
    # 2. Try to grab the existing Master File
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=latest_key)
        existing_csv = response['Body'].read().decode('utf-8')
        existing_df = pd.read_csv(StringIO(existing_csv))
        
        # 3. Append the new data to the bottom of the master file
        combined_df = pd.concat([existing_df, today_df], ignore_index=True)
        
        # 4. Remove exact duplicates (if script runs twice in one day, it keeps the most recent run)
        combined_df = combined_df.drop_duplicates(subset=['Date', 'Ticker'], keep='last')
        print(f"Appended today's data to existing master file for {index_display_name}.")
        
    except s3_client.exceptions.NoSuchKey:
        # If the file doesn't exist yet, today's data becomes the brand new master file!
        print(f"No existing master file found. Creating a new one for {index_display_name}.")
        combined_df = today_df
    except Exception as e:
        print(f"Error reading master file for {index_display_name}: {e}. Proceeding with today's data only.")
        combined_df = today_df

    # Convert combined DataFrame to CSV string
    csv_buffer = StringIO()
    combined_df.to_csv(csv_buffer, index=False)
    final_csv_string = csv_buffer.getvalue()

    # 5. Save the updated Master file back to 'data/today/' for the Dashboard
    s3_client.put_object(Bucket=bucket_name, Key=latest_key, Body=final_csv_string)
    print(f"Successfully updated Dashboard file: {latest_key}")

    # 6. Save a replica to 'data/historical-archive/' for immutable daily backups
    year = today_obj.strftime('%Y')
    month = today_obj.strftime('%m')
    archive_key = f"data/historical-archive/{index_id}/{year}/{month}/{today_str}_{index_id}_archive.csv"
    s3_client.put_object(Bucket=bucket_name, Key=archive_key, Body=final_csv_string)
    print(f"Successfully backed up to Archive: {archive_key}")

    # 7. Save the error log if any stocks failed
    if error_dict:
        error_key = f"data/errors/{today_str}_{index_id}_errors.json"
        s3_client.put_object(Bucket=bucket_name, Key=error_key, Body=json.dumps(error_dict, indent=4))

def main():
    today_obj = datetime.today()
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set!")
        
    print("Fetching and verifying ticker lists...")
    
    # The 100% Automated North American Pipeline
    datasets = {
        'sp500':    {'display': 'SP500',    'tickers': get_cached_tickers(bucket_name, 'sp500', get_sp500_tickers())},
        'sp400':    {'display': 'SP400',    'tickers': get_cached_tickers(bucket_name, 'sp400', get_sp400_tickers())},
        'sp600':    {'display': 'SP600',    'tickers': get_cached_tickers(bucket_name, 'sp600', get_sp600_tickers())},
        'tsx':      {'display': 'TSX',      'tickers': get_cached_tickers(bucket_name, 'tsx', get_tsx_tickers())}
    }

    # Loop through each active index
    for index_id, meta in datasets.items():
        tickers = meta['tickers']
        index_display_name = meta['display']
        
        if not tickers:
            print(f"Skipping {index_display_name} due to empty ticker list.")
            continue
            
        print(f"\n--- Starting data collection for {index_display_name} ({len(tickers)} tickers) ---")
        
        successful_data = []
        errors = {}

        for i, ticker in enumerate(tickers):
            # Print progress every 50 tickers
            if i % 50 == 0 and i > 0:
                print(f"Processed {i}/{len(tickers)} tickers for {index_display_name}...")
                
            data = get_yahoo_data(ticker)
            
            if 'Error' in data:
                errors[ticker] = data['Error']
            else:
                successful_data.append(data)
                
            # Crucial 1-second delay to prevent Yahoo Finance from blocking our IP
            time.sleep(1)

        print(f"Finished {index_display_name}. Success: {len(successful_data)}, Errors: {len(errors)}")

        # Convert to DataFrame and push to S3 pipeline
        if successful_data:
            today_df = pd.DataFrame(successful_data)
            upload_index_to_s3(today_df, errors, today_obj, bucket_name, index_id, index_display_name)
        else:
            print(f"No successful data collected for {index_display_name}. Skipping S3 upload.")

    print("\nAll daily data collection complete!")

if __name__ == "__main__":
    main()
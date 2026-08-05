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
        tickers = [str(ticker).replace('.', '-') for ticker in tickers]
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
        return tickers
    except Exception as e:
        print(f"Notice: Dynamic S&P 600 fetch failed ({e}).")
        return []

def get_tsx_tickers():
    try:
        tables = pd.read_html('https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index')
        df = tables[1]
        tickers = df['Symbol'].tolist()
        tickers = [f"{str(ticker).replace('.', '-')}.TO" for ticker in tickers]
        return tickers
    except Exception as e:
        print(f"Notice: Dynamic TSX fetch failed ({e}).")
        return []

def get_cached_tickers(bucket_name, index_id, fresh_tickers):
    s3_client = boto3.client('s3')
    cache_key = f'data/ticker_lists/{index_id}_cached_tickers.csv'
    
    if fresh_tickers and len(fresh_tickers) > 0:
        try:
            df = pd.DataFrame({'Ticker': fresh_tickers})
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3_client.put_object(Bucket=bucket_name, Key=cache_key, Body=csv_buffer.getvalue())
        except Exception:
            pass
        return fresh_tickers
    else:
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=cache_key)
            df = pd.read_csv(StringIO(response['Body'].read().decode('utf-8')))
            return df['Ticker'].tolist()
        except Exception:
            return []

def get_yahoo_data(ticker, index_name):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info):
            return {'Ticker': ticker, 'Error': 'No valid pricing data found.'}

        close = info.get('regularMarketPreviousClose', info.get('previousClose', info.get('currentPrice')))

        # Aligned exactly to your requested historical columns, plus the new ones
        dict_rating = {
            'Ticker': ticker,
            'Company_Name': info.get('shortName', ticker),
            'index': index_name,
            'min_target': info.get('targetLowPrice'),
            'max_target': info.get('targetHighPrice'),
            'target_mean': info.get('targetMeanPrice'),
            'target_median': info.get('targetMedianPrice'),
            'number_analysts': info.get('numberOfAnalystOpinions'),
            'close': close,
            'open': info.get('regularMarketOpen'),
            'high': info.get('regularMarketDayHigh'),
            'low': info.get('regularMarketDayLow'),
            'industry': info.get('industry', 'Unknown'),
            'sector': info.get('sector', 'Unknown'),
            'bid': info.get('bid'),
            'ask': info.get('ask'),
            'bid_from_mean_target': None, # Calculated below
            
            # Formatted exactly to your original script's casing
            'heldPercentInsiders': info.get('heldPercentInsiders'),
            'heldPercentInstitutions': info.get('heldPercentInstitutions'),
            'trailingPE': info.get('trailingPE'),
            'forwardPE': info.get('forwardPE'),
            'earningsGrowth': info.get('earningsGrowth'),
            'revenueGrowth': info.get('revenueGrowth'),
            'grossMargins': info.get('grossMargins'),
            'ebitdaMargins': info.get('ebitdaMargins'),
            'operatingMargins': info.get('operatingMargins'),
            'shortRatio': info.get('shortRatio'),
            'numberOfAnalystOpinions': info.get('numberOfAnalystOpinions'),
            'recommendationMean': info.get('recommendationMean'),
            'close_from_mean_target': None, # Calculated below
            'averageAnalystRating': info.get('averageAnalystRating'),
            'trailingPegRatio': info.get('trailingPegRatio'),
            
            # New Extracted Fundamentals
            'totalRevenue': info.get('totalRevenue'),
            'ebitda': info.get('ebitda'),
            'netIncomeToCommon': info.get('netIncomeToCommon'),
            'trailingEps': info.get('trailingEps'),
            'forwardEps': info.get('forwardEps'),
            'priceToBook': info.get('priceToBook'),
            'debtToEquity': info.get('debtToEquity'),
            'currentRatio': info.get('currentRatio'),
            'quickRatio': info.get('quickRatio'),
            'totalCash': info.get('totalCash'),
            'totalDebt': info.get('totalDebt'),
            'freeCashflow': info.get('freeCashflow'),
            'operatingCashflow': info.get('operatingCashflow'),
            'returnOnAssets': info.get('returnOnAssets'),
            'returnOnEquity': info.get('returnOnEquity'),
            'dividendYield': info.get('dividendYield'),
            'payoutRatio': info.get('payoutRatio'),
            
            # Volume and Market Data
            'volume': info.get('volume', info.get('regularMarketVolume')),
            'averageVolume': info.get('averageVolume'),
            'beta': info.get('beta'),
            'fiftyDayAverage': info.get('fiftyDayAverage'),
            'twoHundredDayAverage': info.get('twoHundredDayAverage'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
            'sharesShort': info.get('sharesShort'),
            'shortPercentOfFloat': info.get('shortPercentOfFloat'),
            'floatShares': info.get('floatShares')
        }
        
        # Safely calculate the targets
        if dict_rating['target_mean'] and dict_rating['close']:
            dict_rating['close_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['close']) / dict_rating['close']) * 100
            
        if dict_rating['target_mean'] and dict_rating['bid'] and dict_rating['bid'] > 0:
            dict_rating['bid_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['bid']) / dict_rating['bid']) * 100

        return dict_rating
    
    except Exception as e:
        return {'Ticker': ticker, 'Error': str(e)}

def save_and_append_to_s3(today_df, bucket_name, index_id, index_display_name, s3_client):
    """
    Downloads existing master file, appends today's data, deduplicates, and re-uploads.
    """
    s3_key = f"data/today/{index_id}_latest.csv"
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        existing_csv = response['Body'].read().decode('utf-8')
        existing_df = pd.read_csv(StringIO(existing_csv), low_memory=False)
        
        # Standardize column headers just in case
        if 'Date' in existing_df.columns:
            existing_df.rename(columns={'Date': 'date'}, inplace=True)
        if 'ticker' in existing_df.columns:
            existing_df.rename(columns={'ticker': 'Ticker'}, inplace=True)
            
        combined_df = pd.concat([existing_df, today_df], ignore_index=True)
        
        # Drop duplicates to ensure we don't double-append if the script runs twice
        combined_df = combined_df.drop_duplicates(subset=['date', 'Ticker'], keep='last')
        print(f"Appended today's data to master file for {index_display_name}. Total rows: {len(combined_df)}")
        
    except s3_client.exceptions.NoSuchKey:
        print(f"No existing master file found. Creating a new one for {index_display_name}.")
        combined_df = today_df
    except Exception as e:
        print(f"Error reading master file for {index_display_name}: {e}. Proceeding with today's data only.")
        combined_df = today_df

    csv_buffer = StringIO()
    combined_df.to_csv(csv_buffer, index=False)
    s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=csv_buffer.getvalue())

def main():
    today_obj = datetime.today()
    today_str = today_obj.strftime('%Y-%m-%d')
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set!")
        
    s3_client = boto3.client('s3')
    print("Fetching and verifying ticker lists...")
    
    datasets = {
        'sp500': {'display': 'SP500', 'tickers': get_cached_tickers(bucket_name, 'sp500', get_sp500_tickers())},
        'sp400': {'display': 'SP400', 'tickers': get_cached_tickers(bucket_name, 'sp400', get_sp400_tickers())},
        'sp600': {'display': 'SP600', 'tickers': get_cached_tickers(bucket_name, 'sp600', get_sp600_tickers())},
        'tsx':   {'display': 'TSX',   'tickers': get_cached_tickers(bucket_name, 'tsx', get_tsx_tickers())}
    }

    for index_id, meta in datasets.items():
        tickers = meta['tickers']
        index_display_name = meta['display']
        
        if not tickers:
            continue
            
        print(f"\n--- Starting data collection for {index_display_name} ({len(tickers)} tickers) ---")
        successful_data = []

        for i, ticker in enumerate(tickers):
            if i % 50 == 0 and i > 0:
                print(f"Processed {i}/{len(tickers)} tickers for {index_display_name}...")
                
            data = get_yahoo_data(ticker, index_display_name)
            
            if 'Error' not in data:
                successful_data.append(data)
                
            time.sleep(1) # Be polite to Yahoo Finance

        if successful_data:
            today_df = pd.DataFrame(successful_data)
            # Use lowercase 'date' to perfectly align with historical side-collected data
            today_df.insert(0, 'date', today_str) 
            
            save_and_append_to_s3(today_df, bucket_name, index_id, index_display_name, s3_client)
            
            # Archive backup
            archive_key = f"data/historical-archive/{index_id}/{today_obj.strftime('%Y')}/{today_obj.strftime('%m')}/{today_str}_{index_id}_archive.csv"
            csv_buffer = StringIO()
            today_df.to_csv(csv_buffer, index=False)
            s3_client.put_object(Bucket=bucket_name, Key=archive_key, Body=csv_buffer.getvalue())

if __name__ == "__main__":
    main()
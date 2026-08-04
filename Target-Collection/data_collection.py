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
        tables = pd.read_html('https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index')
        df = tables[1]
        tickers = df['Symbol'].tolist()
        tickers = [f"{str(ticker).replace('.', '-')}.TO" for ticker in tickers]
        print(f"Successfully fetched {len(tickers)} live TSX Composite tickers from Wikipedia.")
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
        except Exception as e:
            print(f"Notice: Could not save backup cache for {index_id} ({e}).")
        return fresh_tickers
    else:
        print(f"Warning: Live fetch for {index_id} failed. Attempting to load from S3 backup...")
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=cache_key)
            existing_csv_string = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(existing_csv_string))
            fallback_tickers = df['Ticker'].tolist()
            print(f"Success! Loaded {len(fallback_tickers)} backup tickers for {index_id}.")
            return fallback_tickers
        except Exception as e:
            print(f"Critical: No backup cache found for {index_id} ({e}). Skipping.")
            return []

def get_yahoo_data(ticker, index_name):
    """
    Fetches an exhaustive list of financial metrics for a single ticker.
    Using .get() safely returns None (blank) if the data doesn't exist, preventing crashes!
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info):
            return {'Ticker': ticker, 'Error': 'No valid pricing data found.'}

        # Handle Base Prices
        close = info.get('regularMarketPreviousClose', info.get('previousClose', info.get('currentPrice')))

        # The Master Dictionary
        dict_rating = {
            'Ticker': ticker,
            'Company_Name': info.get('shortName', ticker),
            'index': index_name,
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            
            # Core Price & Target Data
            'close': close,
            'open': info.get('regularMarketOpen'),
            'high': info.get('regularMarketDayHigh'),
            'low': info.get('regularMarketDayLow'),
            'bid': info.get('bid'),
            'ask': info.get('ask'),
            'volume': info.get('volume', info.get('regularMarketVolume')),
            'averageVolume': info.get('averageVolume'),
            
            'min_target': info.get('targetLowPrice'),
            'max_target': info.get('targetHighPrice'),
            'target_mean': info.get('targetMeanPrice'),
            'target_median': info.get('targetMedianPrice'),
            'number_analysts': info.get('numberOfAnalystOpinions'),
            'recommendationMean': info.get('recommendationMean'),
            'averageAnalystRating': info.get('averageAnalystRating'),
            
            # Core Financials (Growth & Margins)
            'trailingPE': info.get('trailingPE'),
            'forwardPE': info.get('forwardPE'),
            'trailingPegRatio': info.get('trailingPegRatio'),
            'earningsGrowth': info.get('earningsGrowth'),
            'revenueGrowth': info.get('revenueGrowth'),
            'grossMargins': info.get('grossMargins'),
            'ebitdaMargins': info.get('ebitdaMargins'),
            'operatingMargins': info.get('operatingMargins'),
            
            # Raw Revenue & Earnings (Absolute Values)
            'totalRevenue': info.get('totalRevenue'),
            'ebitda': info.get('ebitda'),
            'netIncomeToCommon': info.get('netIncomeToCommon'),
            'trailingEps': info.get('trailingEps'),
            'forwardEps': info.get('forwardEps'),
            
            # Deep Value & Balance Sheet
            'priceToBook': info.get('priceToBook'),
            'enterpriseToRevenue': info.get('enterpriseToRevenue'),
            'enterpriseToEbitda': info.get('enterpriseToEbitda'),
            'debtToEquity': info.get('debtToEquity'),
            'currentRatio': info.get('currentRatio'),
            'quickRatio': info.get('quickRatio'),
            'totalCash': info.get('totalCash'),
            'totalDebt': info.get('totalDebt'),
            'freeCashflow': info.get('freeCashflow'),
            'operatingCashflow': info.get('operatingCashflow'),

            # Profitability & Efficiency
            'returnOnAssets': info.get('returnOnAssets'),
            'returnOnEquity': info.get('returnOnEquity'),
            
            # Dividends & Income
            'dividendYield': info.get('dividendYield'),
            'payoutRatio': info.get('payoutRatio'),
            'fiveYearAvgDividendYield': info.get('fiveYearAvgDividendYield'),

            # Technicals & Momentum
            'beta': info.get('beta'),
            'fiftyDayAverage': info.get('fiftyDayAverage'),
            'twoHundredDayAverage': info.get('twoHundredDayAverage'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
            
            # Ownership & Short Squeeze Mechanics
            'heldPercentInsiders': info.get('heldPercentInsiders'),
            'heldPercentInstitutions': info.get('heldPercentInstitutions'),
            'shortRatio': info.get('shortRatio'),
            'sharesShort': info.get('sharesShort'),
            'shortPercentOfFloat': info.get('shortPercentOfFloat'),
            'impliedSharesOutstanding': info.get('impliedSharesOutstanding'),
            'floatShares': info.get('floatShares')
        }
        
        # Safely compute calculated metrics
        if dict_rating['target_mean'] and dict_rating['close']:
            dict_rating['close_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['close']) / dict_rating['close']) * 100
        else:
            dict_rating['close_from_mean_target'] = None
            
        if dict_rating['target_mean'] and dict_rating['bid'] and dict_rating['bid'] > 0:
            dict_rating['bid_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['bid']) / dict_rating['bid']) * 100
        else:
            dict_rating['bid_from_mean_target'] = None

        return dict_rating
    
    except Exception as e:
        return {'Ticker': ticker, 'Error': str(e)}

def upload_index_to_s3(today_df, error_dict, today_obj, bucket_name, index_id, index_display_name):
    s3_client = boto3.client('s3')
    today_str = today_obj.strftime('%Y-%m-%d')
    
    if 'Date' not in today_df.columns:
        today_df.insert(0, 'Date', today_str)

    latest_key = f"data/today/{index_id}_latest.csv"
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=latest_key)
        existing_csv = response['Body'].read().decode('utf-8')
        existing_df = pd.read_csv(StringIO(existing_csv))
        
        combined_df = pd.concat([existing_df, today_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['Date', 'Ticker'], keep='last')
        print(f"Appended today's data to existing master file for {index_display_name}.")
        
    except s3_client.exceptions.NoSuchKey:
        print(f"No existing master file found. Creating a new one for {index_display_name}.")
        combined_df = today_df
    except Exception as e:
        print(f"Error reading master file for {index_display_name}: {e}. Proceeding with today's data only.")
        combined_df = today_df

    csv_buffer = StringIO()
    combined_df.to_csv(csv_buffer, index=False)
    final_csv_string = csv_buffer.getvalue()

    s3_client.put_object(Bucket=bucket_name, Key=latest_key, Body=final_csv_string)
    print(f"Successfully updated Dashboard file: {latest_key}")

    year = today_obj.strftime('%Y')
    month = today_obj.strftime('%m')
    archive_key = f"data/historical-archive/{index_id}/{year}/{month}/{today_str}_{index_id}_archive.csv"
    s3_client.put_object(Bucket=bucket_name, Key=archive_key, Body=final_csv_string)
    print(f"Successfully backed up to Archive: {archive_key}")

    if error_dict:
        error_key = f"data/errors/{today_str}_{index_id}_errors.json"
        s3_client.put_object(Bucket=bucket_name, Key=error_key, Body=json.dumps(error_dict, indent=4))

def main():
    today_obj = datetime.today()
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set!")
        
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
            print(f"Skipping {index_display_name} due to empty ticker list.")
            continue
            
        print(f"\n--- Starting data collection for {index_display_name} ({len(tickers)} tickers) ---")
        
        successful_data = []
        errors = {}

        for i, ticker in enumerate(tickers):
            if i % 50 == 0 and i > 0:
                print(f"Processed {i}/{len(tickers)} tickers for {index_display_name}...")
                
            # Pass the index_display_name so it gets stamped on every row!
            data = get_yahoo_data(ticker, index_display_name)
            
            if 'Error' in data:
                errors[ticker] = data['Error']
            else:
                successful_data.append(data)
                
            time.sleep(1)

        print(f"Finished {index_display_name}. Success: {len(successful_data)}, Errors: {len(errors)}")

        if successful_data:
            today_df = pd.DataFrame(successful_data)
            upload_index_to_s3(today_df, errors, today_obj, bucket_name, index_id, index_display_name)
        else:
            print(f"No successful data collected for {index_display_name}. Skipping S3 upload.")

    print("\nAll daily data collection complete!")

if __name__ == "__main__":
    main()
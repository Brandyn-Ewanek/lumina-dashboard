import urllib.request
import json
import os
import time
import boto3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO

def get_fred_data(series_id, api_key, start_date):
    """Fetches a single time-series from the FRED API."""
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&observation_start={start_date}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        observations = data.get('observations', [])
        clean_obs = []
        for obs in observations:
            if obs['value'] != '.':
                clean_obs.append({'Date': obs['date'], series_id: float(obs['value'])})
                
        return pd.DataFrame(clean_obs)
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.DataFrame()

def compute_pearson_correlation(x, y):
    """Fast vector numpy Pearson correlation calculation."""
    if len(x) < 10 or len(y) < 10:
        return 0.0
    valid_mask = ~(np.isnan(x) | np.isnan(y))
    x_clean, y_clean = x[valid_mask], y[valid_mask]
    if len(x_clean) < 10:
        return 0.0
    std_x, std_y = np.std(x_clean), np.std(y_clean)
    if std_x == 0 or std_y == 0:
        return 0.0
    corr = np.corrcoef(x_clean, y_clean)[0, 1]
    return 0.0 if np.isnan(corr) else float(corr)

def generate_macro_correlations(master_macro_df, s3_client, bucket_name):
    """
    Crunches all stock price history against 120+ macro metrics across
    multiple timeframes and lag offsets (0 to 6 months).
    Identifies high-conviction macro correlations (|r| >= 0.65) and uploads to S3.
    """
    print("\n--- Starting Nightly Macro Correlation Discovery Engine ---", flush=True)
    indices = ['sp500', 'sp400', 'sp600', 'tsx']
    all_stocks_data = []

    # Fetch stock data from S3
    for idx in indices:
        try:
            res = s3_client.get_object(Bucket=bucket_name, Key=f'data/today/{idx}_latest.csv')
            csv_str = res['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_str), low_memory=False)
            if 'Date' in df.columns and 'Ticker' in df.columns:
                all_stocks_data.append(df)
        except Exception as e:
            print(f"Notice: Could not load stock data for {idx}: {e}", flush=True)

    if not all_stocks_data:
        print("Warning: No stock files loaded. Skipping correlation matrix computation.", flush=True)
        return

    combined_stocks_df = pd.concat(all_stocks_data, ignore_index=True)
    combined_stocks_df['Date'] = pd.to_datetime(combined_stocks_df['Date'])
    
    # Prepare macro dataframe index
    macro_df = master_macro_df.copy()
    macro_df['Date'] = pd.to_datetime(macro_df['Date'])
    macro_df.set_index('Date', inplace=True)
    macro_cols = [c for c in macro_df.columns if c != 'Date']

    # CRITICAL UPDATE: Only scan over the MAX timeframe to ensure long-term structural validity
    timeframes = {'MAX': 1000} 
    lags = [0, 1, 2, 3, 4, 5, 6]
    
    discovered_plays = []
    unique_tickers = combined_stocks_df['Ticker'].dropna().unique()
    print(f"Scanning {len(unique_tickers)} stocks across {len(macro_cols)} macro metrics...", flush=True)

    processed_tickers = 0
    for ticker in unique_tickers:
        processed_tickers += 1
        if processed_tickers % 100 == 0:
            print(f"Correlation Engine Progress: {processed_tickers}/{len(unique_tickers)} tickers scanned...", flush=True)

        stock_sub = combined_stocks_df[combined_stocks_df['Ticker'] == ticker].sort_values('Date')
        if len(stock_sub) < 15:
            continue

        stock_sub = stock_sub.set_index('Date')
        close_col = 'Close_Price' if 'Close_Price' in stock_sub.columns else 'close'
        if close_col not in stock_sub.columns:
            continue

        latest_date = stock_sub.index.max()

        for tf_label, days in timeframes.items():
            cutoff = latest_date - pd.Timedelta(days=days)
            tf_stock = stock_sub[stock_sub.index >= cutoff]
            if len(tf_stock) < 10:
                continue

            for macro_col in macro_cols:
                macro_series = macro_df[macro_col].dropna()
                if len(macro_series) < 15:
                    continue

                for lag_m in lags:
                    if lag_m == 0:
                        aligned = tf_stock[[close_col]].join(macro_series, how='inner').dropna()
                    else:
                        # Shift macro date backwards by lag_m months
                        lagged_stock = tf_stock.copy()
                        lagged_stock['Lagged_Date'] = lagged_stock.index.map(lambda d: d - pd.DateOffset(months=lag_m))
                        aligned = lagged_stock.reset_index().set_index('Lagged_Date')[[close_col, 'Date']].join(macro_series, how='inner').dropna()

                    if len(aligned) < 10:
                        continue

                    x = aligned[close_col].values
                    y = aligned[macro_col].values
                    r = compute_pearson_correlation(x, y)

                    # Keep only high-conviction mathematical correlations (|r| >= 0.65)
                    if abs(r) >= 0.65:
                        discovered_plays.append({
                            "ticker": str(ticker),
                            "macro": str(macro_col),
                            "timeframe": tf_label,
                            "lag": int(lag_m),
                            "correlation": float(r),
                            "abs_corr": float(abs(r))
                        })

    # Deduplicate: Keep highest abs correlation per ticker + macro combination
    df_results = pd.DataFrame(discovered_plays)
    if not df_results.empty:
        df_results = df_results.sort_values('abs_corr', ascending=False)
        df_results = df_results.drop_duplicates(subset=['ticker', 'macro'], keep='first')
        df_results = df_results.sort_values('abs_corr', ascending=False)

        top_results = df_results.drop(columns=['abs_corr']).head(300).to_dict(orient='records')
        print(f"Found {len(top_results)} high-conviction macro correlations (|r| >= 0.65).", flush=True)

        # Upload top correlations JSON to S3 Data Lake
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key='dashboard/macro/top_macro_correlations.json',
                Body=json.dumps(top_results, indent=2),
                ContentType='application/json'
            )
            print("Successfully uploaded top_macro_correlations.json to S3 Data Lake!", flush=True)
        except Exception as e:
            print(f"Error uploading top_macro_correlations.json to S3: {e}", flush=True)

def main():
    print("Waking up Global Macro Collector & Correlation Engine...")
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    fred_api_key = os.environ.get('FRED_API_KEY')
    
    if not bucket_name or not fred_api_key:
        print("CRITICAL ERROR: Missing S3_BUCKET_NAME or FRED_API_KEY environment variables.")
        return

    s3_client = boto3.client('s3')

    # Dynamic start date calculation
    oldest_date = datetime.now() - timedelta(days=900) 
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key='data/today/sp500_latest.csv')
        df = pd.read_csv(StringIO(response['Body'].read().decode('utf-8')))
        if 'Date' in df.columns:
            min_date_str = df['Date'].min()
            oldest_date = datetime.strptime(min_date_str, '%Y-%m-%d')
            print(f"Found earliest stock record: {min_date_str}")
    except Exception as e:
        print(f"Could not read stock data for dynamic date, using fallback: {e}")
    
    safe_date = (oldest_date - timedelta(days=360)).strftime('%Y-%m-%d')
    print(f"Fetching macro data starting from: {safe_date}")

    # Master metric dictionary
    metrics = {
        "USEPUINDXD": "News_Economic_Policy_Uncertainty", "VIXCLS": "US_VIX_Volatility",
        "STLFSI4": "US_Financial_Stress_Index", "UMCSENT": "US_Consumer_Sentiment",
        "NFCI": "Chicago_Fed_Financial_Conditions", "FEDFUNDS": "US_Fed_Funds_Rate",
        "DGS10": "US_10_Year_Treasury", "DGS2": "US_2_Year_Treasury",
        "T10Y2Y": "US_Yield_Curve_Inversion", "MORTGAGE30US": "US_30_Year_Mortgage",
        "BAMLH0A0HYM2": "US_High_Yield_Junk_Spread", "BAA10Y": "US_Corporate_Bond_Spread",
        "M2SL": "US_M2_Money_Supply", "WALCL": "US_Fed_Total_Assets_Balance_Sheet",
        "CPIAUCSL": "US_CPI_Headline", "CPILFESL": "US_CPI_Core",
        "PCEPI": "US_PCE_Headline", "PCEPILFE": "US_PCE_Core",
        "PPIACO": "US_PPI_Producer_Prices", "WPSFD49207": "US_PPI_Finished_Goods",
        "T5YIFR": "US_5_Year_Inflation_Expectations", "UNRATE": "US_Unemployment_Rate",
        "PAYEMS": "US_Nonfarm_Payrolls", "ICSA": "US_Initial_Jobless_Claims",
        "JTSJOL": "US_JOLTS_Job_Openings", "CES0500000003": "US_Average_Hourly_Earnings",
        "RSAFS": "US_Retail_Sales", "RETAILIRSA": "US_Real_Retail_Sales",
        "PSAVERT": "US_Personal_Saving_Rate", "TOTALSA": "US_Total_Vehicle_Sales",
        "CCLACBW027SBOG": "US_Consumer_Credit_Cards", "HOUST": "US_Housing_Starts",
        "PERMIT": "US_Building_Permits", "EXHOSLUSM495S": "US_Existing_Home_Sales",
        "CSUSHPISA": "US_Case_Shiller_Home_Price_Index", "INDPRO": "US_Industrial_Production",
        "CUMFNS": "US_Capacity_Utilization", "AMTMNO": "US_Manufacturers_New_Orders",
        "NEWORDER": "US_New_Orders_Nondefense_Capital", "BUSINV": "US_Business_Inventories",
        "DGORDER": "US_Durable_Goods_Orders", "ISRATIO": "US_Inventory_to_Sales_Ratio",
        "IRSTCB01CAM156N": "CAN_Central_Bank_Rate", "CPALCY01CAM661N": "CAN_CPI_Inflation",
        "LRUNTTTTCAM156S": "CAN_Unemployment_Rate", "CANGDPNQDSMEI": "CAN_GDP_Growth",
        "CANPROINDMISMEI": "CAN_Industrial_Production", "HOUSTCAA156NCEN": "CAN_Housing_Starts",
        "DEXCAUS": "FX_CAD_to_USD", "DCOILWTICO": "CMDTY_WTI_Crude_Oil",
        "DCOILBRENTEU": "CMDTY_Brent_Crude", "PNGASEUUSDM": "CMDTY_Natural_Gas",
        "GOLDAMGBD228NLBM": "CMDTY_Gold_Price", "PCOPPUSDM": "CMDTY_Copper_Price",
        "PIORECRUSDM": "CMDTY_Iron_Ore", "WPU012": "CMDTY_Raw_Materials_Index",
        "CHNGDPNQDSMEI": "CHN_GDP_Growth", "CHNPROINDMISMEI": "CHN_Industrial_Production",
        "CHNCPALCY01GYM661N": "CHN_CPI_Inflation", "DEXCHUS": "FX_CNY_to_USD",
        "EZBGPDPQ": "EUR_GDP_Growth", "EZBCPI01EZM661N": "EUR_CPI_Inflation",
        "IR3TIB01EZM156N": "EUR_Interbank_Rate", "DEXUSEU": "FX_EUR_to_USD",
        "GBRPROINDMISMEI": "UK_Industrial_Production", "DEXUSUK": "FX_GBP_to_USD",
        "JPNPROINDMISMEI": "JPN_Industrial_Production", "JPNCPIALLMINMEI": "JPN_CPI_Inflation",
        "DEXJPUS": "FX_JPY_to_USD", "DTWEXBGS": "FX_Trade_Weighted_USD_Index",
        "BOPGSTB": "US_Trade_Balance_Goods_Services", "XTEXVA01CNM667S": "CHN_Total_Exports"
    }

    master_dates = pd.date_range(start=safe_date, end=datetime.now().strftime('%Y-%m-%d'))
    master_df = pd.DataFrame(index=master_dates)
    master_df.index.name = 'Date'

    total = len(metrics)
    count = 1

    for series_id, col_name in metrics.items():
        if count % 15 == 0 or count == total:
            print(f"[{count}/{total}] Fetching macro metrics from FRED...")
        df = get_fred_data(series_id, fred_api_key, safe_date)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.rename(columns={series_id: col_name}, inplace=True)
            df = df[~df.index.duplicated(keep='last')]
            master_df = master_df.join(df, how='left')
        time.sleep(0.5)
        count += 1

    master_df = master_df.ffill().dropna(how='all')
    master_df.reset_index(inplace=True)
    master_df['Date'] = master_df['Date'].dt.strftime('%Y-%m-%d')

    # Upload global macro CSV
    csv_buffer = StringIO()
    master_df.to_csv(csv_buffer, index=False)
    
    try:
        s3_client.put_object(
            Bucket=bucket_name, 
            Key="data/macro/global_macro_latest.csv", 
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        print(f"SUCCESS: Macro dataset saved to s3://{bucket_name}/data/macro/global_macro_latest.csv")
    except Exception as e:
        print(f"S3 Upload Failed: {e}")

    # Run Automated Nightly Correlation Pipeline
    generate_macro_correlations(master_df, s3_client, bucket_name)

if __name__ == "__main__":
    main()
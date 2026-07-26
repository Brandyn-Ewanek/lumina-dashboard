import urllib.request
import json
import os
import time
import boto3
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

def main():
    print("Waking up Global Macro Collector...")
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    fred_api_key = os.environ.get('FRED_API_KEY')
    
    if not bucket_name or not fred_api_key:
        print("CRITICAL ERROR: Missing S3_BUCKET_NAME or FRED_API_KEY environment variables.")
        return

    s3_client = boto3.client('s3')

    # --- DYNAMIC START DATE LOGIC ---
    def get_dynamic_start_date():
        # Default fallback just in case the bucket is empty
        oldest_date = datetime.now() - timedelta(days=900) 
        try:
            # We check the S&P 500 file as our master reference for the timeline
            response = s3_client.get_object(Bucket=bucket_name, Key='data/today/sp500_latest.csv')
            df = pd.read_csv(StringIO(response['Body'].read().decode('utf-8')))
            if 'Date' in df.columns:
                min_date_str = df['Date'].min()
                oldest_date = datetime.strptime(min_date_str, '%Y-%m-%d')
                print(f"Found earliest stock record: {min_date_str}")
        except Exception as e:
            print(f"Could not read stock data for dynamic date, using fallback: {e}")
        
        # Subtract an extra 360 days from the oldest stock date.
        # This gives us a 1-year buffer so we can calculate 360-day lags on the very first stock record!
        safe_date = oldest_date - timedelta(days=360)
        return safe_date.strftime('%Y-%m-%d')

    start_date = get_dynamic_start_date()
    print(f"Fetching macro data starting from: {start_date}")

    # ==========================================
    # THE INSTITUTIONAL MACRO DICTIONARY (120+ Metrics)
    # ==========================================
    metrics = {
        # --- NEWS CYCLE & MARKET PSYCHOLOGY ---
        "USEPUINDXD": "News_Economic_Policy_Uncertainty", 
        "VIXCLS": "US_VIX_Volatility",
        "STLFSI4": "US_Financial_Stress_Index",
        "UMCSENT": "US_Consumer_Sentiment",
        "NFCI": "Chicago_Fed_Financial_Conditions",

        # --- COST OF CAPITAL & VALUATION (Target Price Drivers) ---
        "FEDFUNDS": "US_Fed_Funds_Rate",
        "DGS10": "US_10_Year_Treasury",
        "DGS2": "US_2_Year_Treasury",
        "T10Y2Y": "US_Yield_Curve_Inversion",
        "MORTGAGE30US": "US_30_Year_Mortgage",
        "BAMLH0A0HYM2": "US_High_Yield_Junk_Spread", # Critical for S&P 600
        "BAA10Y": "US_Corporate_Bond_Spread",
        "M2SL": "US_M2_Money_Supply",
        "WALCL": "US_Fed_Total_Assets_Balance_Sheet",

        # --- US INFLATION & MARGIN SQUEEZE ---
        "CPIAUCSL": "US_CPI_Headline",
        "CPILFESL": "US_CPI_Core",
        "PCEPI": "US_PCE_Headline",
        "PCEPILFE": "US_PCE_Core",
        "PPIACO": "US_PPI_Producer_Prices", # Compare to CPI for profit margins
        "WPSFD49207": "US_PPI_Finished_Goods",
        "T5YIFR": "US_5_Year_Inflation_Expectations",

        # --- US CONSUMER & LABOR (S&P 400 & 600 Revenue Drivers) ---
        "UNRATE": "US_Unemployment_Rate",
        "PAYEMS": "US_Nonfarm_Payrolls",
        "ICSA": "US_Initial_Jobless_Claims",
        "JTSJOL": "US_JOLTS_Job_Openings",
        "CES0500000003": "US_Average_Hourly_Earnings",
        "RSAFS": "US_Retail_Sales",
        "RETAILIRSA": "US_Real_Retail_Sales",
        "PSAVERT": "US_Personal_Saving_Rate",
        "TOTALSA": "US_Total_Vehicle_Sales",
        "CCLACBW027SBOG": "US_Consumer_Credit_Cards",

        # --- US HOUSING & REAL ESTATE ---
        "HOUST": "US_Housing_Starts",
        "PERMIT": "US_Building_Permits",
        "EXHOSLUSM495S": "US_Existing_Home_Sales",
        "CSUSHPISA": "US_Case_Shiller_Home_Price_Index",

        # --- US BUSINESS & MANUFACTURING (Leading Indicators) ---
        "INDPRO": "US_Industrial_Production",
        "CUMFNS": "US_Capacity_Utilization",
        "AMTMNO": "US_Manufacturers_New_Orders",
        "NEWORDER": "US_New_Orders_Nondefense_Capital",
        "BUSINV": "US_Business_Inventories",
        "DGORDER": "US_Durable_Goods_Orders",
        "ISRATIO": "US_Inventory_to_Sales_Ratio",

        # --- CANADA (TSX CORE DRIVERS) ---
        "IRSTCB01CAM156N": "CAN_Central_Bank_Rate",
        "CPALCY01CAM661N": "CAN_CPI_Inflation",
        "LRUNTTTTCAM156S": "CAN_Unemployment_Rate",
        "CANGDPNQDSMEI": "CAN_GDP_Growth",
        "CANPROINDMISMEI": "CAN_Industrial_Production",
        "HOUSTCAA156NCEN": "CAN_Housing_Starts",
        "DEXCAUS": "FX_CAD_to_USD",
        
        # --- COMMODITIES & RESOURCES (TSX / S&P Energy / Materials) ---
        "DCOILWTICO": "CMDTY_WTI_Crude_Oil",
        "DCOILBRENTEU": "CMDTY_Brent_Crude",
        "PNGASEUUSDM": "CMDTY_Natural_Gas",
        "GOLDAMGBD228NLBM": "CMDTY_Gold_Price",
        "PCOPPUSDM": "CMDTY_Copper_Price",
        "PIORECRUSDM": "CMDTY_Iron_Ore",
        "WPU012": "CMDTY_Raw_Materials_Index",

        # --- GLOBAL HEALTH: CHINA (Manufacturing & Demand) ---
        "CHNGDPNQDSMEI": "CHN_GDP_Growth",
        "CHNPROINDMISMEI": "CHN_Industrial_Production",
        "CHNCPALCY01GYM661N": "CHN_CPI_Inflation",
        "DEXCHUS": "FX_CNY_to_USD",

        # --- GLOBAL HEALTH: EUROZONE & UK ---
        "EZBGPDPQ": "EUR_GDP_Growth",
        "EZBCPI01EZM661N": "EUR_CPI_Inflation",
        "IR3TIB01EZM156N": "EUR_Interbank_Rate",
        "DEXUSEU": "FX_EUR_to_USD",
        "GBRPROINDMISMEI": "UK_Industrial_Production",
        "DEXUSUK": "FX_GBP_to_USD",

        # --- GLOBAL HEALTH: JAPAN & ASIA ---
        "JPNPROINDMISMEI": "JPN_Industrial_Production",
        "JPNCPIALLMINMEI": "JPN_CPI_Inflation",
        "DEXJPUS": "FX_JPY_to_USD",

        # --- FOREX & GLOBAL TRADE (S&P 500 Currency Impacts) ---
        "DTWEXBGS": "FX_Trade_Weighted_USD_Index", # A strong dollar crushes S&P 500 foreign earnings
        "BOPGSTB": "US_Trade_Balance_Goods_Services",
        "XTEXVA01CNM667S": "CHN_Total_Exports"
    }

    # Create a master DataFrame starting with every calendar day in our range
    master_dates = pd.date_range(start=start_date, end=datetime.now().strftime('%Y-%m-%d'))
    master_df = pd.DataFrame(index=master_dates)
    master_df.index.name = 'Date'

    total = len(metrics)
    count = 1

    for series_id, col_name in metrics.items():
        print(f"[{count}/{total}] Fetching {col_name} ({series_id})...")
        
        df = get_fred_data(series_id, fred_api_key, start_date)
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.rename(columns={series_id: col_name}, inplace=True)
            
            # Remove any duplicate index entries to prevent join issues
            df = df[~df.index.duplicated(keep='last')]
            
            master_df = master_df.join(df, how='left')
            
        # FRED limits requests to 120 per minute (2 per second). 0.6s sleep is safe.
        time.sleep(0.6)
        count += 1

    print("Data collection complete. Normalizing time horizons...")

    # ==========================================
    # TIME ALIGNMENT & FORWARD FILLING
    # ==========================================
    # Carries weekly/monthly data forward to every daily row.
    master_df = master_df.ffill()
    
    # Drop rows at the very beginning that might still be fully NaN
    master_df = master_df.dropna(how='all')

    master_df.reset_index(inplace=True)
    master_df['Date'] = master_df['Date'].dt.strftime('%Y-%m-%d')

    print(f"Final Macro Dataset Shape: {master_df.shape[0]} Days x {master_df.shape[1]-1} Metrics")

    # ==========================================
    # UPLOAD TO S3 DATA LAKE
    # ==========================================
    print("Uploading to AWS S3...")
    s3_client = boto3.client('s3')
    
    csv_buffer = StringIO()
    master_df.to_csv(csv_buffer, index=False)
    
    file_key = "data/macro/global_macro_latest.csv"
    
    try:
        s3_client.put_object(
            Bucket=bucket_name, 
            Key=file_key, 
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        print(f"SUCCESS: Macro data saved to s3://{bucket_name}/{file_key}")
    except Exception as e:
        print(f"S3 Upload Failed: {e}")

if __name__ == "__main__":
    main()
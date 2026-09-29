import pandas as pd
import yfinance as yf
import boto3
import json
import time
import os
import requests
import re
from datetime import datetime
from io import StringIO

# ==========================================
# 1. AWS BEDROCK CONFIGURATION
# ==========================================
KB_ID = "UCDIEAZIRS"

# We split the clients: KB is in your local CA region, Nova models run best in US East 1
try:
    bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='ca-central-1')
    bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
except Exception as e:
    print(f"Warning: Could not initialize Bedrock clients. Error: {e}")

def analyze_news_severity(ticker, news_block):
    """Queries Pinecone via Bedrock and uses Nova Lite to grade news severity."""
    if not news_block or "No recent news available" in news_block:
        return 0.5, "None"
        
    case_studies = "No historical context available."
    
    # 1. Retrieve Historical Precedents from Pinecone
    try:
        retrieval_resp = bedrock_agent.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': f"Impact of: {news_block}"},
            retrievalConfiguration={'vectorSearchConfiguration': {'numberOfResults': 3}}
        )
        results = retrieval_resp.get('retrievalResults', [])
        if results:
            case_studies = "\n\n".join([r['content']['text'] for r in results])
    except Exception as e:
        print(f"[{ticker}] KB Retrieval skipped/failed: {e}")

    # 2. Score Severity via Amazon Nova Lite
    system_prompt = """You are an elite quantitative equity analyst. 
Analyze the recent news headlines for the stock and grade the catalyst's severity from 0.0 to 1.0.
0.0 = Harmless / Temporary Macro Noise / Positive News
0.5 = Moderate Headwind
1.0 = Structural Failure / Catastrophic Risk / Fraud

Use the provided historical precedents to inform your score if relevant.
Return ONLY a valid JSON object with exactly two keys: "catalyst_type" (a short 3-word string) and "severity_score" (a float). Do not include markdown formatting."""
    
    prompt = f"Stock: {ticker}\nLive News: {news_block}\n\nHistorical Case Studies:\n{case_studies}"
    
    try:
        response = bedrock_runtime.converse(
            modelId='amazon.nova-lite-v1:0',
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            system=[{"text": system_prompt}],
            inferenceConfig={"temperature": 0.1, "maxTokens": 200}
        )
        
        output_text = response['output']['message']['content'][0]['text']
        
        # Clean up JSON if Nova wrapped it in markdown
        match = re.search(r'\{.*\}', output_text, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
        else:
            result = json.loads(output_text)
            
        return float(result.get('severity_score', 0.5)), str(result.get('catalyst_type', 'Unknown'))
        
    except Exception as e:
        print(f"[{ticker}] Nova inference failed: {e}")
        return 0.5, "Unscored"

# ==========================================
# 2. TICKER LISTS
# ==========================================
def get_sp500_tickers():
    tickers = [
        # Software
        'ADBE', 'ADSK', 'AKAM', 'ANSS', 'CDNS', 'CRM', 'CTAS', 'CTSH', 'EPAM', 'FFIV',
        'FIS', 'FISV', 'FTNT', 'INTU', 'IT', 'MSFT', 'NOW', 'NLOK', 'NTAP', 'NVDA',
        'ORCL', 'PAYC', 'PTC', 'SNPS', 'TYL', 'VRSN', 'ZM', 'ADP', 'CDK', 'DASH',
        'DAY', 'FICO', 'HUBS', 'PANW', 'PAYX', 'WDAY', 'DDOG', 'CRWD', 'MDB', 'OKTA',
        'PLTR', 'SNOW', 'TEAM', 'ZS', 'ALTI','AI', 'PLTR',
        # Hardware
        'AAPL', 'AMD', 'AMAT', 'APH', 'ARW', 'AVGO', 'CCI', 'CSCO', 'GLW', 'HPE', 'HPQ',
        'INTC', 'KEYS', 'KLAC', 'LRCX', 'MCHP', 'MU', 'MSI', 'NXPI', 'QCOM', 'QRVO',
        'STX', 'SWKS', 'TEL', 'TER', 'TXN', 'XLNX', 'ZBRA', 'ADI', 'JNPR', 'TRMB',
        'ASML', 'SMCI', 'TSM', 'CLS', 'MRVL',
        # IT Services & Consulting
        'ACN', 'CDW', 'COGN', 'DXC', 'FIS', 'FISV', 'GPN', 'IBM', 'IQV', 'LDOS',
        'MMC', 'AON', 'BR', 'JKHY', 'ROP', 'V', 'MA', 'PYPL',
        # Pharmaceuticals
        'ABBV', 'AGN', 'AMGN', 'BIIB', 'BMY', 'GILD', 'INCY', 'JNJ', 'LLY', 'MRK',
        'MRNA', 'OGN', 'PFE', 'REGN', 'VRTX','ZTS',
        # Medical Devices & Supplies
        'ABT', 'BAX', 'BDX', 'BIO', 'BSX', 'CAH', 'COO', 'DHR', 'EW', 'HOLX', 'IDXX',
        'ISRG', 'MDT', 'MCK', 'STE', 'SYK', 'TFX', 'TMO', 'ZBH','A', 'ALGN', 'PODD',
        'RMD', 'TECH', 'WAT', 'WST',
        # Healthcare Services
        'AET', 'ANTM', 'CI', 'CNC', 'CVS', 'DGX', 'DVA', 'HCA', 'HUM', 'LH', 'UHS',
        'UNH','COR', 'ELV', 'EVH',
        # Banks
        'BAC', 'BBT', 'BEN', 'BK', 'BLK', 'C', 'CFG', 'CMA', 'COF', 'DFS', 'FITB',
        'FRC', 'HBAN', 'HIG', 'JPM', 'KEY', 'KMI', 'M&T', 'MET', 'MS', 'NTRS', 'PNC',
        'RF', 'RJF', 'SBNY', 'SCHW', 'SIVB', 'STT', 'TFC', 'TRV', 'USB', 'WFC',
        'ZION', 'AJG', 'GS', 'SPGI', 'MCO', 'NDAQ',
        # Insurance
        'AFL', 'AIG', 'AIZ', 'ALL', 'AXP', 'BRK.B', 'CB', 'CINF', 'CME', 'GL', 'LNC',
        'MMC', 'PRU', 'RE', 'TRV', 'WRB','ACGL', 'AON', 'BRO', 'FDS', 'PFG', 'PGR',
        # Investment Management
        'AMP', 'APO', 'AXP', 'BLK', 'BR', 'IVZ', 'MKTX', 'MSCI', 'TROW', 'BX',
        'ICE', 'KKR', 'HOOD',
        # Retail
        'AMZN', 'AZO', 'BBWI', 'BBY', 'COST', 'DG', 'DLTR', 'DPZ', 'EBAY', 'EXPE',
        'F', 'GPS', 'HD', 'KMX', 'KR', 'LOW', 'LVS', 'LYV', 'MCD', 'MHK', 'NCLH',
        'NKE', 'ORLY', 'PENN', 'POOL', 'PVH', 'RCL', 'RL', 'ROST', 'SBUX', 'TGT',
        'TJX', 'TPR', 'UA', 'UAA', 'ULTA', 'VFC', 'WHR', 'WSM', 'WYNN', 'YUM','ABNB',
        'BKNG', 'CHRW', 'CMG', 'DHI', 'DRI', 'GPN', 'GRMN', 'HLT', 'MAR', 'NVR',
        'PHM', 'ROK', 'SHW', 'TJX', 'WM',
        # Automobiles
        'F', 'GM', 'HOG', 'LKQ', 'PCAR', 'TSLA', 'NIO',
        # Media & Entertainment
        'CMCSA', 'DIS', 'DISCA', 'DISCK', 'DISH', 'FOX', 'FOXA', 'LYV', 'MTCH',
        'NFLX', 'NWSA', 'NWS', 'TWTR', 'WBD', 'GOOG', 'GOOGL', 'IPG', 'META',
        'OMC', 'PARA', 'T', 'TMUS', 'UBER', 'VZ','BIDU',
        # Food & Beverage
        'ADM', 'CAG', 'CPB', 'GIS', 'HRL', 'HSY', 'K', 'KHC', 'KMB', 'KO', 'LW',
        'MDLZ', 'MNST', 'MO', 'PEP', 'SJM', 'STZ', 'SYY', 'TAP', 'TSN','BF-B',
        'KDP', 'MKC',
        # Household & Personal Products
        'CHD', 'CL', 'CLX', 'EL', 'KMB', 'PG',
        # Aerospace & Defense
        'BA', 'GD', 'HII', 'HON', 'LHX', 'LMT', 'NOC', 'RTX', 'TXT','GE', 'TDG',
        # Machinery
        'CAT', 'CMI', 'DE', 'DOV', 'EMR', 'ETN', 'EXPD', 'FAST', 'FMC', 'FTV', 'HWM',
        'IR', 'ITW', 'JCI', 'MAS', 'MLM', 'MMM', 'PH', 'PNR', 'ROK', 'ROP', 'SNA',
        'SWK', 'TT', 'URI', 'VMC', 'WAB','AOS', 'AME', 'CARR', 'CSX', 'DAL', 'DE',
        'GNRC', 'JCI', 'LUV', 'NSC', 'OTIS', 'PCAR', 'PH', 'TT', 'UAL', 'UNP',
        'UPS', 'XYL','XMTR', 'PRLB',
        # Construction & Engineering
        'AAL', 'ALLE', 'AVY', 'BALL', 'CARR', 'CF', 'DHI', 'DRE', 'ECL', 'EFX', 'ESS',
        'FLR', 'GPC', 'J', 'LEN', 'LUMN', 'OTIS', 'PKG', 'PLD', 'PWR', 'RSG', 'SEE',
        'SPG', 'TDG', 'VNO', 'WELL', 'WRK', 'XYL','BLDR', 'J', 'LEN', 'MAS', 'SITE',
        'VMC', 'WST',
        # Oil & Gas Exploration & Production
        'APA', 'COP', 'CTRA', 'DVN', 'EOG', 'FANG', 'HES', 'MRO', 'MPC', 'OXY',
        'PXD', 'SLB', 'VLO', 'XOM','CVX',
        # Oil & Gas Midstream & Refining
        'EPD', 'KMI', 'OKE', 'PSX', 'TRGP', 'WMB','MPC', 'ENB',
        # Oil & Gas Equipment & Services
        'BKR', 'FSLR', 'HAL', 'HP',
        # Renewable Energy
        'ENPH', 'NEE', 'SEDG','CEG', 'SOL',
        # Electric / Utilities
        'AEE', 'AEP', 'AES', 'ATO', 'AWK', 'CMS', 'CNP', 'D', 'DTE', 'DUK', 'ED',
        'EIX', 'ES', 'ETR', 'EVRG', 'EXC', 'FE', 'NEE', 'NI', 'NRG', 'PEG', 'PPL',
        'PNW', 'SO', 'SRE', 'WEC', 'XEL','LNT','WCN',
        # Chemicals
        'ALB', 'APD', 'CE', 'DD', 'DOW', 'EMN', 'IFF', 'LYB', 'MOS', 'PPG',
        'SHW','LIN', 'WLK', 'MX',
        # Metals & Mining
        'FCX', 'NEM', 'NUE', 'NTR',
        # REITs
        'ARE', 'AVB', 'BXP', 'CPT', 'CCI', 'DLR', 'DRE', 'EQIX', 'EQR', 'ESS',
        'EXR', 'FRT', 'HST', 'IRM', 'KIM', 'MAA', 'O', 'PEAK', 'PLD', 'PSA',
        'REG', 'SBAC', 'SPG', 'UDR', 'VNO', 'WELL','AMT', 'PSA', 'WY', 'VTR'
    ]
    return [str(t).replace('.', '-') for t in list(set(tickers))]

def get_sp400_tickers():
    tickers = [
        # Communication Services
        'IEX', 'LBRDA', 'LBRDK', 'LSXMA', 'LSXMK', 'MTCH', 'NYT', 'OMC', 'SIRI',
        'WWE', 'Z', 'ZG','SATS','WMG',
        # Consumer Discretionary
        'AAP', 'AN', 'ANF', 'ARMK', 'ALV', 'BBWI', 'BBY', 'BWA', 'BC', 'BLDR',
        'BURL', 'CPRI', 'KMX', 'CAVA', 'CZR', 'DECK', 'DKS', 'DPZ', 'DKNG', 'EXPE',
        'FIVE', 'FND', 'FL', 'GRMN', 'GIII', 'GPC', 'HAS', 'HGV', 'H', 'JACK', 'KSS',
        'LEA', 'LAD', 'LYV', 'LEN', 'M', 'VAC', 'MAT', 'MHK', 'NWL', 'JWN', 'ORLY',
        'PAG', 'PLNT', 'POOL', 'PHM', 'RL', 'ROST', 'RCL', 'TPR', 'TSCO', 'TNL',
        'ULTA', 'MTN', 'VFC', 'WHR', 'WSM', 'YUM', 'ALLE', 'BJ', 'NXT','TNL', 'TPH',
        # Consumer Staples
        'BF-B', 'CPB', 'CAG', 'CHD', 'CLX', 'DAR', 'EL', 'FLO', 'GIS', 'HRL', 'HSY',
        'INGR', 'K', 'KDP', 'KMB', 'LW', 'MKC', 'MDLZ', 'MNST', 'PEP', 'SJM', 'STZ',
        'SYY', 'TSN', 'WBA', 'POST', 'ACI', 'BRBR', 'CASY',  'USFD',
        # Energy
        'APA', 'BKR', 'COP', 'CVX', 'DVN', 'EOG', 'HAL', 'HES', 'KMI', 'MRO', 'MPC',
        'OXY', 'PSX', 'PXD', 'SLB', 'TRGP', 'VLO', 'WMB', 'XOM', 'CLR', 'AM',  'AR',
        'TPL', 'VNOM',
        # Financials
        'ACGL', 'AFG', 'AFL', 'ALL', 'ALLY', 'AMG', 'AON', 'AXON', 'AIG', 'AIZ',
        'AMP', 'AWI', 'AXS', 'BAC', 'BEN', 'BK', 'BLK', 'BRO', 'BRK-B', 'C', 'CBOE',
        'CB', 'CINF', 'CMA', 'CFG', 'COF', 'DFS', 'ERIE', 'FDS', 'FITB', 'FHN', 'GL',
        'GS', 'HBAN', 'HIG', 'IVZ', 'JPM', 'KEY', 'L', 'LNC', 'MKTX', 'MMC', 'MET',
        'MCO', 'MS', 'MSCI', 'NDAQ', 'NAVI', 'NTRS', 'ORI', 'PFG', 'PGR', 'PNC', 'PRU',
        'RJF', 'RF', 'RE', 'SCHW', 'STT', 'SIVB', 'TFC', 'TRV', 'TROW', 'USB', 'WRB',
        'WFC', 'WTW', 'ZION','ASB', 'BHF', 'CADE', 'ESNT', 'FULT', 'HLNE', 'IBKR',
        'JXN', 'ONB', 'UMBF', 'WAL',
        # Health Care
        'ACHC', 'AMED', 'AVTR', 'BIO', 'BMRN', 'CRL', 'COO', 'XRAY', 'EHC', 'EXAS',
        'EXEL', 'GMED', 'HOLX', 'IDXX', 'PODD', 'IART', 'IQV', 'JAZZ', 'LNTH', 'MASI',
        'MEDP', 'MTD', 'MOH', 'NBIX', 'PEN', 'DGX', 'RVTY', 'SRPT', 'TNDM', 'TFX',
        'THC', 'UTHR', 'UHS', 'VEEV', 'WST', 'ZBH', 'ICUI','AVNT', 'CYTK', 'ILMN',
        # Industrials
        'AYI', 'ACM', 'AGCO', 'AL', 'ALK', 'AAL', 'APG', 'AIT', 'CAR', 'BWXT', 'BAH',
        'BYD', 'BRC', 'BCO', 'CSL', 'CLH', 'FIX', 'CPA', 'CW', 'EME', 'FLR', 'GATX',
        'GNRC', 'GGG', 'HEI', 'HWM', 'HUBB', 'HII', 'ITT', 'J', 'JBLU', 'KNX', 'LDOS',
        'LII', 'MTZ', 'NDSN', 'NVT', 'OSK', 'OC', 'PSN', 'RBA', 'RRX', 'RSG', 'R',
        'SAIA', 'SNA', 'LUV', 'SPR', 'TXT', 'TTC', 'TDG', 'TGI', 'UAL', 'URI', 'VMI',
        'WCN', 'WCC', 'XPO', 'ZBRA', 'JBT', 'AAON', 'ATI', 'CNH', 'WWD', 'ZWS',
        # Information Technology
        'AKAM', 'ALGM', 'DOX', 'AMKR', 'APPF', 'ARW', 'ASGN', 'AVT', 'BDC', 'BILL',
        'BLKB', 'CDNS', 'CDW', 'COHR', 'CVLT', 'GLW', 'DDOG', 'DOCU', 'DBX', 'DT',
        'ENPH', 'EPAM', 'FFIV', 'FICO', 'FLEX', 'FTNT', 'G', 'GFS', 'GDDY', 'GWRE',
        'HPE', 'HPQ', 'IBM', 'INTC', 'JBL', 'JNPR', 'KEYS', 'KLAC', 'LRCX', 'MCHP',
        'MU', 'MSI', 'NTAP', 'NLOK', 'NVDA', 'PAYC', 'PTC', 'QCOM', 'QRVO', 'RMD',
        'STX', 'SNPS', 'SWKS', 'TEL', 'TER', 'TRMB', 'TYL', 'VRSN', 'WDC', 'ZTS',
        # Materials
        'ALB', 'APD', 'AVY', 'BLL', 'CE', 'CF', 'DD', 'DOW', 'ECL', 'EMN', 'FMC',
        'IFF', 'IP', 'LIN', 'LYB', 'MLM', 'MOS', 'NEM', 'NUE', 'PKG', 'PPG', 'SHW',
        'SEE', 'VMC', 'WRK', 'CE', 'ALTR', 'FN','PSTG','AA', 'ASH', 'ATR', 'AXTA',
        # Real Estate
        'ARE', 'AMT', 'AVB', 'BXP', 'CPT', 'CCI', 'DLR', 'DRE', 'EQIX', 'EQR', 'ESS',
        'EXR', 'FRT', 'HST', 'IRM', 'KIM', 'MAA', 'O', 'PEAK', 'PLD', 'PSA', 'REG',
        'SBAC', 'SPG', 'UDR', 'VTR', 'VNO', 'WELL', 'WY','ADC', 'AMH', 'RHP', 'TRNO',
        # Utilities
        'AEE', 'AEP', 'AES', 'ATO', 'AWK', 'CNP', 'CMS', 'D', 'DTE', 'DUK', 'ED',
        'EIX', 'ES', 'ETR', 'EVRG', 'EXC', 'FE', 'LNT', 'NEE', 'NI', 'NRG', 'PEG',
        'PNW', 'PPL', 'SO', 'SRE', 'WEC', 'XEL', 'ALE', 'BKH'
    ]
    return [str(t).replace('.', '-') for t in list(set(tickers))]

def get_sp600_tickers():
    tickers = [
        # Financials
        'AEL', 'AGO', 'AMBC', 'AMSF', 'ARI', 'ASB', 'BANC', 'BANF', 'BANR', 'BFIN',
        'BHF', 'BOKF', 'CADE', 'CATY', 'CFFN', 'CHCO', 'CNBS', 'COOP', 'CVBF',
        'ESNT', 'EWBC', 'FBC', 'FBP', 'FBSI', 'FULT', 'GBCI', 'GSHD', 'HWC', 'HIFS',
        'HLNE', 'HMN', 'HOPE', 'INDB', 'ISBC', 'LBAI', 'MCY', 'NMIH', 'NBN', 'NPK',
        'OCFC', 'OFG', 'ONB', 'ORRF', 'OSBC', 'PFBC', 'PFSI', 'PROV', 'PJT', 'RNST',
        'SASR', 'SFBS', 'SFST', 'SLM', 'STC', 'SUI', 'TCBI', 'TBBK', 'TRUP', 'UMBF',
        'UCBI', 'VIRT', 'VLY', 'WABC', 'WBS', 'WETF', 'WRLD',
        # Industrials
        'AAN', 'AAON', 'ABM', 'ACA', 'AIN', 'AIR', 'ALG', 'ARCB', 'ATKR', 'AVAV',
        'AZZ', 'B', 'BCC', 'BMI', 'BWFG', 'CARS', 'CBIZ', 'CHX', 'CR', 'CRS', 'CSWI',
        'CSX', 'CTOS', 'CVGI', 'DCI', 'DXPE', 'DY', 'EPAC', 'ESE', 'FSS', 'GBX',
        'GFF', 'GVA', 'GTLS', 'HCSG', 'HNI', 'HURC', 'IBP', 'IDCC', 'ITGR', 'ITRI',
        'KAI', 'KAR', 'KFY', 'KMT', 'LMAT', 'LNN', 'MATW', 'MGRC', 'MOG.A', 'MSA',
        'MWA', 'MYE', 'NPO', 'NSC', 'PAC', 'PBI', 'PRA', 'RBC', 'ROLL', 'RUSHA',
        'RYAM', 'SCPH', 'SKY', 'SLVM', 'SPXC', 'STRL', 'SXI', 'TILE', 'TKR', 'TRN',
        'UFPT', 'UNF', 'VRRM', 'WERN', 'WLDN', 'ZWS',
        # Information Technology
        'ACIW', 'ACLS', 'ADTN', 'AGYS', 'ALRM', 'AOSL', 'ATEN', 'AVID', 'BOX', 'CALX',
        'CCOI', 'CEVA', 'CLSK', 'CNXC', 'CRVL', 'CSGS', 'DIOD', 'DOCN', 'EBC', 'ENVA',
        'EVTC', 'EXTR', 'HLIT', 'HSTM', 'IMKTA', 'IMPINJ', 'INSP', 'IRDM', 'ITI',
        'LPSN', 'LRN', 'LUNA', 'MARA', 'MSTR', 'NABL', 'NATI', 'NVEI', 'PAYO', 'PCTI',
        'PI', 'PRFT', 'PRGS', 'PSTG', 'QLIK', 'QNST', 'QTWO', 'RDWR', 'SPSC', 'SREV',
        'STRT', 'SMTC', 'TDC', 'TESS', 'TTEC', 'TWOU', 'UIS', 'UPLD',
        # Health Care
        'ABCB', 'ADUS', 'AGTI', 'AHCO', 'AMEH', 'AMN', 'AMPH', 'ANGO', 'ANIK', 'ANIP',
        'AORT', 'AROW', 'AVNS', 'BCPC', 'BLFS', 'CASH', 'CCRN', 'CERE', 'CHNG',
        'COLL', 'COR', 'CORT', 'CPRX', 'CPSI', 'CUTR', 'DGII', 'EHC', 'GKOS', 'HAE',
        'HAIN', 'HRMY', 'HSKA', 'ICUI', 'IDN', 'INVA', 'IRTC', 'ITGR', 'LGH', 'LMAT',
        'MMSI', 'NEO', 'NHC', 'OPCH', 'PAHC', 'PDCO', 'PGNY', 'PHM', 'PRVA', 'PTGX',
        'RDNT', 'SEM', 'SGRY', 'TGTX', 'TMDX', 'TRHC', 'VCEL', 'VIVO',
        # Consumer Discretionary
        'ABG', 'AEO', 'ALGT', 'AMWD', 'ASO', 'ATGE', 'BOOT', 'BSET', 'CENT', 'CHEF',
        'CHGG', 'CNK', 'CONN', 'CSV', 'CVCO', 'DORM', 'DRH', 'EAT', 'ETH', 'FIGS',
        'FLXS', 'FOSL', 'FTDR', 'FUN', 'GCO', 'GOLF', 'GPI', 'GRBK', 'HBI', 'HCI',
        'HIBB', 'HVT', 'IPAR', 'IRG', 'KBAL', 'KFY', 'KTB', 'LC', 'LESL', 'LFMN',
        'LINC', 'LSEA', 'MCRI', 'MESA', 'MGPI', 'MOV', 'MSGS', 'MYRG', 'OLLI', 'PLCE',
        'PLAY', 'PRG', 'PZZA', 'RCII', 'RENT', 'SAH', 'SCVL', 'SHAK', 'SHOO', 'SIG',
        'SKY', 'SONO', 'SP', 'TILE', 'TPH', 'TR', 'VVI', 'WGO', 'WSM', 'WWW', 'XPEL', 'YOU',
        # Real Estate
        'AAT', 'ADC', 'AHH', 'AKR', 'ALEX', 'APLE', 'BRT', 'CIO', 'CSR', 'CUBE', 'CUZ',
        'DEA', 'DHC', 'EPRT', 'FCPT', 'FSP', 'GEO', 'GNL', 'GTY', 'HTA', 'IIPR', 'INDT',
        'LSI', 'LTC', 'MPW', 'NHI', 'NXRT', 'OFC', 'OPI', 'OUT', 'PCH', 'PEB', 'PFBC',
        'RHP', 'RLJ', 'SHO', 'SIR', 'SLG', 'SRC', 'STAG', 'STOR', 'TRNO', 'UNIT',
        'VER', 'WRE', 'XHR',
        # Materials
        'ACA', 'APOG', 'ASIX', 'ATI', 'AVD', 'BCC', 'CENX', 'CSTM', 'DRD', 'ESE', 'GFF',
        'GMS', 'HWKN', 'IBP', 'KALU', 'KOP', 'KRUS', 'MLP', 'MTX', 'OLN', 'PLPC', 'PLXS',
        'RYAM', 'SCHN', 'SLVM', 'SMG', 'SUM', 'SYNL', 'TMST', 'TRS', 'UFPI', 'USLM', 'WOR',
        # Energy
        'AROC', 'ARCH', 'BCEI', 'BRY', 'BSM', 'CDEV', 'CIVI', 'CNX', 'CRC', 'CRK',
        'ESTE', 'GLOP', 'HCC', 'LPI', 'MNRL', 'MTDR', 'NOG', 'OAS', 'OII', 'OIS',
        'PDCE', 'POWL', 'PXD', 'ROCC', 'SLCA', 'SM', 'TDW', 'TUSK', 'VTLE', 'WHD',
        # Utilities
        'ALE', 'AVA', 'AWR', 'BKH', 'MGEE', 'NJR', 'NWN', 'OTTR', 'SJI', 'SR', 'SWX',
        'UGI', 'UPL', 'WTRG', 'YORW',
        # Communication Services
        'ADTN', 'ATNI', 'CCOI', 'CNSL', 'GOGO', 'GTN', 'IMAX', 'LILA', 'LILAK', 'MSG',
        'PRTH', 'SABR', 'SBGI', 'SATS', 'TIGO', 'USM'
    ]
    return [str(t).replace('.', '-') for t in list(set(tickers))]

def get_tsx_tickers():
    tickers = [
        # Financials
        'RY.TO', 'TD.TO', 'BMO.TO', 'BNS.TO', 'CM.TO', 'NA.TO', 'MFC.TO', 'SLF.TO', 'IFC.TO', 'POW.TO', 'GWO.TO',
        'BAM.TO', 'BN.TO', 'FFH.TO', 'ONEX.TO', 'GSY.TO', 'EQB.TO', 'HCG.TO', 'CWB.TO', 'LB.TO',
        # Energy
        'SU.TO', 'CNQ.TO', 'ENB.TO', 'TRP.TO', 'PPL.TO', 'CVE.TO', 'IMO.TO', 'WCP.TO', 'ARX.TO', 'TOU.TO', 'CPG.TO',
        'VET.TO', 'MEG.TO', 'ERF.TO', 'BIR.TO', 'BTE.TO', 'ATH.TO', 'PEY.TO', 'CJ.TO', 'KEC.TO',
        # Materials
        'NTR.TO', 'GOLD.TO', 'AEM.TO', 'FNV.TO', 'TECK-B.TO', 'WPM.TO', 'K.TO', 'CCO.TO', 'ELD.TO', 'IMG.TO',
        'LUN.TO', 'IVN.TO', 'FM.TO', 'CS.TO', 'BTO.TO', 'ABX.TO', 'FR.TO', 'PAAS.TO', 'GFL.TO', 'WFG.TO',
        # Industrials
        'CNR.TO', 'CP.TO', 'WCN.TO', 'TRI.TO', 'BBD-B.TO', 'AC.TO', 'TFII.TO', 'CAE.TO', 'WSP.TO', 'SNC.TO', 'ARE.TO',
        'ATS.TO', 'BAD.TO', 'CLS.TO', 'MAXR.TO', 'NFI.TO', 'RUS.TO', 'STN.TO', 'TIH.TO',
        # Information Technology
        'SHOP.TO', 'CSU.TO', 'GIB-A.TO', 'OTEX.TO', 'LSPD.TO', 'KXS.TO', 'BB.TO', 'DND.TO', 'ENGH.TO', 'KIN.TO',
        'REAL.TO', 'TEC.TO',
        # Consumer Discretionary
        'ATD.TO', 'MG.TO', 'L.TO', 'MRU.TO', 'WN.TO', 'CTC-A.TO', 'DOL.TO', 'QSR.TO', 'ATZ.TO', 'BRP.TO', 'GFL.TO',
        'ROOT.TO', 'WEED.TO',
        # Communication Services
        'BCE.TO', 'T.TO', 'RCI-B.TO', 'QBR-B.TO', 'SJR-B.TO', 'CGX.TO', 'TCS.TO',
        # Real Estate
        'AP-UN.TO', 'CAR-UN.TO', 'GRT-UN.TO', 'IIP-UN.TO', 'KMP-UN.TO', 'MRG-UN.TO', 'REI-UN.TO',
        'SRU-UN.TO', 'BEI-UN.TO',
        # Utilities
        'FTS.TO', 'AQN.TO', 'EMA.TO', 'H.TO', 'CPX.TO', 'INE.TO', 'NPI.TO', 'RNW.TO', 'TA.TO',
        # Consumer Staples
        'SAP.TO', 'EMP-A.TO', 'MFI.TO', 'PBH.TO', 'NWC.TO', 'JWEL.TO',
        # Health Care
        'WEED.TO', 'APHA.TO', 'CRON.TO', 'TLRY.TO', 'HEXO.TO', 'OGI.TO', 'VFF.TO',
        'MG.TO', 'BDI.TO', 'T.TO'
    ]
    # CRITICAL FIX: DO NOT replace dots with dashes here! Yahoo Finance requires the .TO suffix!
    return [str(t) for t in list(set(tickers))]

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

# ==========================================
# 3. MEMORY BANK & DATA FETCHING
# ==========================================
def get_historical_state(bucket_name, index_id, s3_client):
    """Loads yesterday's S3 file so we can inherit scores if the news hasn't changed."""
    state = {}
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=f"data/today/{index_id}_latest.csv")
        df = pd.read_csv(StringIO(response['Body'].read().decode('utf-8', errors='replace')), low_memory=False)
        
        date_col = 'date' if 'date' in df.columns else 'Date'
        latest_df = df.sort_values(date_col).groupby('Ticker').last().reset_index()
        
        for _, row in latest_df.iterrows():
            state[row['Ticker']] = {
                'recent_news': row.get('recent_news', ''),
                'news_severity': row.get('news_severity', 0.5),
                'catalyst_type': row.get('catalyst_type', 'Inherited'),
                'temporary_scare_score': row.get('temporary_scare_score', 0.0),
                'margin_of_safety_score': row.get('margin_of_safety_score', 0.0)
            }
        print(f"Loaded memory state for {len(state)} tickers from {index_id}.")
    except Exception as e:
        print(f"Could not load memory state for {index_id} (Starting fresh): {e}")
    return state

def get_yahoo_data(ticker, index_name):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info):
            return {'Ticker': ticker, 'Error': 'No valid pricing data found.'}

        close = info.get('regularMarketPreviousClose', info.get('previousClose', info.get('currentPrice')))

        # ==============================================================
        # NEW YAHOO FINANCE API PARSER (Fixed for nested JSON & ISO Dates)
        # ==============================================================
        news_block = "No recent news available."
        try:
            news_items = stock.news
            if news_items:
                formatted_news = []
                for item in news_items[:5]:
                    title = item.get('title', item.get('content', 'No Title'))
                    
                    provider = item.get('provider', {})
                    if isinstance(provider, dict):
                        publisher = provider.get('displayName', 'Unknown Publisher')
                    else:
                        publisher = item.get('publisher', 'Unknown Publisher')
                    
                    pub_time = item.get('pubDate', item.get('providerPublishTime', item.get('publishTime')))
                    date_str = "Unknown Date"
                    
                    if pub_time:
                        if isinstance(pub_time, str):
                            # It's an ISO string like '2026-09-24T09:14:38Z'
                            date_str = pub_time.split('T')[0]
                        else:
                            # It's a UNIX timestamp integer
                            try:
                                date_str = datetime.fromtimestamp(int(pub_time)).strftime('%Y-%m-%d')
                            except (ValueError, TypeError):
                                date_str = "Unknown Date"
                        
                    formatted_news.append(f"[{date_str}] {title} ({publisher})")
                
                if formatted_news:
                    news_block = " | ".join(formatted_news)
        except Exception as e:
            print(f"Notice: Could not parse news for {ticker}: {e}")
            pass

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
            'bid_from_mean_target': None,
            
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
            'close_from_mean_target': None,
            'averageAnalystRating': info.get('averageAnalystRating'),
            'trailingPegRatio': info.get('trailingPegRatio'),
            
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
            
            'volume': info.get('volume', info.get('regularMarketVolume')),
            'averageVolume': info.get('averageVolume'),
            'beta': info.get('beta'),
            'fiftyDayAverage': info.get('fiftyDayAverage'),
            'twoHundredDayAverage': info.get('twoHundredDayAverage'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
            'sharesShort': info.get('sharesShort'),
            'shortPercentOfFloat': info.get('shortPercentOfFloat'),
            'floatShares': info.get('floatShares'),
            
            # Attaching the extracted news block
            'recent_news': news_block
        }
        
        if dict_rating['target_mean'] and dict_rating['close']:
            dict_rating['close_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['close']) / dict_rating['close']) * 100
            
        if dict_rating['target_mean'] and dict_rating['bid'] and dict_rating['bid'] > 0:
            dict_rating['bid_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['bid']) / dict_rating['bid']) * 100

        return dict_rating
    
    except Exception as e:
        return {'Ticker': ticker, 'Error': str(e)}

# ==========================================
# 4. S3 FILE MANAGEMENT
# ==========================================
def save_and_append_to_s3(today_df, bucket_name, index_id, index_display_name, s3_client):
    s3_key = f"data/today/{index_id}_latest.csv"
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        existing_csv = response['Body'].read().decode('utf-8', errors='replace')
        existing_df = pd.read_csv(StringIO(existing_csv), low_memory=False)
        
        if 'Date' in existing_df.columns:
            existing_df.rename(columns={'Date': 'date'}, inplace=True)
        if 'ticker' in existing_df.columns:
            existing_df.rename(columns={'ticker': 'Ticker'}, inplace=True)
            
        combined_df = pd.concat([existing_df, today_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['date', 'Ticker'], keep='last')
        
        csv_buffer = StringIO()
        combined_df.to_csv(csv_buffer, index=False)
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=csv_buffer.getvalue())
        print(f"✅ Appended today's data to master file for {index_display_name}. Total rows: {len(combined_df)}")
        
    except s3_client.exceptions.NoSuchKey:
        print(f"⚠️ No existing master file found for {index_display_name}. Creating new.")
        csv_buffer = StringIO()
        today_df.to_csv(csv_buffer, index=False)
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=csv_buffer.getvalue())
        
    except Exception as e:
        print(f"CRITICAL ERROR reading master file for {index_display_name}: {e}")
        print("ABORTING APPEND to protect historical data. Saving today's data as a backup instead.")
        backup_key = f"data/error-backups/{index_id}_today_only.csv"
        csv_buffer = StringIO()
        today_df.to_csv(csv_buffer, index=False)
        s3_client.put_object(Bucket=bucket_name, Key=backup_key, Body=csv_buffer.getvalue())

# ==========================================
# 5. MAIN EXECUTION PIPELINE
# ==========================================
def main():
    today_obj = datetime.today()
    today_str = today_obj.strftime('%Y-%m-%d')
    
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set!")
        
    s3_client = boto3.client('s3')
    print("Waking up Lumina Data Pipeline with Amazon Nova AI Gatekeeper...")
    
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
            
        print(f"\n--- Starting AI pipeline for {index_display_name} ({len(tickers)} tickers) ---")
        
        # 1. Load the Memory Bank
        historical_state = get_historical_state(bucket_name, index_id, s3_client)
        successful_data = []

        for i, ticker in enumerate(tickers):
            if i % 50 == 0 and i > 0:
                print(f"Processed {i}/{len(tickers)} tickers for {index_display_name}...")
                
            # Fetch Live Data
            data = get_yahoo_data(ticker, index_display_name)
            
            if 'Error' not in data:
                past_state = historical_state.get(ticker, {})
                past_news = past_state.get('recent_news', '')
                live_news = data.get('recent_news', '')
                
                # AI Gatekeeper Check
                if not live_news or live_news == past_news or "No recent news available" in live_news:
                    # Inherit previous scores to save AWS runtime/money
                    severity = past_state.get('news_severity', 0.5)
                    catalyst = past_state.get('catalyst_type', 'Inherited/None')
                else:
                    # Trigger Bedrock & Nova Lite for a brand new catalyst
                    print(f"🚨 Breaking News detected for {ticker}. Routing to Amazon Nova...")
                    severity, catalyst = analyze_news_severity(ticker, live_news)
                
                upside_pct = data.get('close_from_mean_target')
                
                # ==============================================================
                # VECTOR 1: "Temporary Scare" Score (Max 35 points)
                # ==============================================================
                if upside_pct is None or upside_pct <= 0:
                    temp_scare_score = 0.0
                else:
                    # Convert percentage to decimal and normalize to an 80% maximum upside scale
                    upside_dec = upside_pct / 100.0
                    u_norm = min(upside_dec / 0.80, 1.0)
                    # Non-linear divergence formula: Punishes high-severity value traps
                    temp_scare_score = 35.0 * (u_norm**0.4) * (1.0 - severity**1.7)
                
                # ==============================================================
                # VECTOR 2: "Margin of Safety" Score (Max 25 points)
                # ==============================================================
                if upside_pct is None or upside_pct <= 0:
                    margin_score = 0.0
                else:
                    upside_dec = upside_pct / 100.0
                    capped_upside = min(upside_dec, 0.50)
                    margin_score = (capped_upside / 0.50) * 25.0
                
                # Append finalized scores
                data['news_severity'] = severity
                data['catalyst_type'] = catalyst
                data['temporary_scare_score'] = round(temp_scare_score, 2)
                data['margin_of_safety_score'] = round(margin_score, 2)
                
                successful_data.append(data)
                
            time.sleep(1) # Yahoo Rate Limit Buffer

        # Upload and Append
        if successful_data:
            today_df = pd.DataFrame(successful_data)
            today_df.insert(0, 'date', today_str) 
            save_and_append_to_s3(today_df, bucket_name, index_id, index_display_name, s3_client)
            
            # Archive backup
            archive_key = f"data/historical-archive/{index_id}/{today_obj.strftime('%Y')}/{today_obj.strftime('%m')}/{today_str}_{index_display_name.upper()} Data.csv"
            try:
                csv_buffer = StringIO()
                today_df.to_csv(csv_buffer, index=False)
                s3_client.put_object(Bucket=bucket_name, Key=archive_key, Body=csv_buffer.getvalue())
            except Exception as e:
                print(f"Note: Could not upload archive backup for {index_id}: {e}")

if __name__ == "__main__":
    main()
import pandas as pd
import yfinance as yf
import boto3
import json
import time
import os
import requests
from datetime import datetime
from io import StringIO

def get_sp500_tickers():
    tickers = [
        'ADBE', 'ADSK', 'AKAM', 'ANSS', 'CDNS', 'CRM', 'CTAS', 'CTSH', 'EPAM', 'FFIV',
        'FIS', 'FISV', 'FTNT', 'INTU', 'IT', 'MSFT', 'NOW', 'NLOK', 'NTAP', 'NVDA',
        'ORCL', 'PAYC', 'PTC', 'SNPS', 'TYL', 'VRSN', 'ZM', 'ADP', 'CDK', 'DASH',
        'DAY', 'FICO', 'HUBS', 'PANW', 'PAYX', 'WDAY', 'DDOG', 'CRWD', 'MDB', 'OKTA',
        'PLTR', 'SNOW', 'TEAM', 'ZS', 'ALTI', 'AI', 'AAPL', 'AMD', 'AMAT', 'APH', 
        'ARW', 'AVGO', 'CCI', 'CSCO', 'GLW', 'HPE', 'HPQ', 'INTC', 'KEYS', 'KLAC', 
        'LRCX', 'MCHP', 'MU', 'MSI', 'NXPI', 'QCOM', 'QRVO', 'STX', 'SWKS', 'TEL', 
        'TER', 'TXN', 'XLNX', 'ZBRA', 'ADI', 'JNPR', 'TRMB', 'ASML', 'SMCI', 'TSM', 
        'CLS', 'MRVL', 'ACN', 'CDW', 'COGN', 'DXC', 'GPN', 'IBM', 'IQV', 'LDOS',
        'MMC', 'AON', 'BR', 'JKHY', 'ROP', 'V', 'MA', 'PYPL', 'ABBV', 'AGN', 'AMGN', 
        'BIIB', 'BMY', 'GILD', 'INCY', 'JNJ', 'LLY', 'MRK', 'MRNA', 'OGN', 'PFE', 
        'REGN', 'VRTX', 'ZTS', 'ABT', 'BAX', 'BDX', 'BIO', 'BSX', 'CAH', 'COO', 
        'DHR', 'EW', 'HOLX', 'IDXX', 'ISRG', 'MDT', 'MCK', 'STE', 'SYK', 'TFX', 
        'TMO', 'ZBH', 'A', 'ALGN', 'PODD', 'RMD', 'TECH', 'WAT', 'WST', 'AET', 
        'ANTM', 'CI', 'CNC', 'CVS', 'DGX', 'DVA', 'HCA', 'HUM', 'LH', 'UHS',
        'UNH', 'COR', 'ELV', 'EVH', 'BAC', 'BBT', 'BEN', 'BK', 'BLK', 'C', 'CFG', 
        'CMA', 'COF', 'DFS', 'FITB', 'FRC', 'HBAN', 'HIG', 'JPM', 'KEY', 'KMI', 
        'M&T', 'MET', 'MS', 'NTRS', 'PNC', 'RF', 'RJF', 'SBNY', 'SCHW', 'SIVB', 
        'STT', 'TFC', 'TRV', 'USB', 'WFC', 'ZION', 'AJG', 'GS', 'SPGI', 'MCO', 
        'NDAQ', 'AFL', 'AIG', 'AIZ', 'ALL', 'AXP', 'BRK.B', 'CB', 'CINF', 'CME', 
        'GL', 'LNC', 'PRU', 'RE', 'WRB', 'ACGL', 'BRO', 'FDS', 'PFG', 'PGR',
        'AMP', 'APO', 'IVZ', 'MKTX', 'MSCI', 'TROW', 'BX', 'ICE', 'KKR', 'HOOD',
        'AMZN', 'AZO', 'BBWI', 'BBY', 'COST', 'DG', 'DLTR', 'DPZ', 'EBAY', 'EXPE',
        'F', 'GPS', 'HD', 'KMX', 'KR', 'LOW', 'LVS', 'LYV', 'MCD', 'MHK', 'NCLH',
        'NKE', 'ORLY', 'PENN', 'POOL', 'PVH', 'RCL', 'RL', 'ROST', 'SBUX', 'TGT',
        'TJX', 'TPR', 'UA', 'UAA', 'ULTA', 'VFC', 'WHR', 'WSM', 'WYNN', 'YUM', 'ABNB',
        'BKNG', 'CHRW', 'CMG', 'DHI', 'DRI', 'GRMN', 'HLT', 'MAR', 'NVR',
        'PHM', 'ROK', 'SHW', 'WM', 'GM', 'HOG', 'LKQ', 'PCAR', 'TSLA', 'NIO',
        'CMCSA', 'DIS', 'DISCA', 'DISCK', 'DISH', 'FOX', 'FOXA', 'MTCH',
        'NFLX', 'NWSA', 'NWS', 'TWTR', 'WBD', 'GOOG', 'GOOGL', 'IPG', 'META',
        'OMC', 'PARA', 'T', 'TMUS', 'UBER', 'VZ', 'BIDU', 'ADM', 'CAG', 'CPB', 
        'GIS', 'HRL', 'HSY', 'K', 'KHC', 'KMB', 'KO', 'LW', 'MDLZ', 'MNST', 'MO', 
        'PEP', 'SJM', 'STZ', 'SYY', 'TAP', 'TSN', 'BF-B', 'KDP', 'MKC', 'CHD', 
        'CL', 'CLX', 'EL', 'PG', 'BA', 'GD', 'HII', 'HON', 'LHX', 'LMT', 'NOC', 
        'RTX', 'TXT', 'GE', 'TDG', 'CAT', 'CMI', 'DE', 'DOV', 'EMR', 'ETN', 'EXPD', 
        'FAST', 'FMC', 'FTV', 'HWM', 'IR', 'ITW', 'JCI', 'MAS', 'MLM', 'MMM', 'PH', 
        'PNR', 'SNA', 'SWK', 'TT', 'URI', 'VMC', 'WAB', 'AOS', 'AME', 'CARR', 
        'CSX', 'DAL', 'GNRC', 'LUV', 'NSC', 'OTIS', 'UAL', 'UNP', 'UPS', 'XYL', 
        'XMTR', 'PRLB', 'AAL', 'ALLE', 'AVY', 'BALL', 'CF', 'DRE', 'ECL', 'EFX', 
        'ESS', 'FLR', 'GPC', 'J', 'LEN', 'LUMN', 'PKG', 'PLD', 'PWR', 'RSG', 'SEE', 
        'SPG', 'VNO', 'WELL', 'WRK', 'BLDR', 'SITE', 'APA', 'COP', 'CTRA', 'DVN', 
        'EOG', 'FANG', 'HES', 'MRO', 'MPC', 'OXY', 'PXD', 'SLB', 'VLO', 'XOM', 'CVX',
        'EPD', 'OKE', 'PSX', 'TRGP', 'WMB', 'ENB', 'BKR', 'FSLR', 'HAL', 'HP',
        'ENPH', 'NEE', 'SEDG', 'CEG', 'SOL', 'AEE', 'AEP', 'AES', 'ATO', 'AWK', 
        'CMS', 'CNP', 'D', 'DTE', 'DUK', 'ED', 'EIX', 'ES', 'ETR', 'EVRG', 'EXC', 
        'FE', 'NI', 'NRG', 'PEG', 'PPL', 'PNW', 'SO', 'SRE', 'WEC', 'XEL', 'LNT', 
        'WCN', 'ALB', 'APD', 'CE', 'DD', 'DOW', 'EMN', 'IFF', 'LYB', 'MOS', 'PPG',
        'LIN', 'WLK', 'MX', 'FCX', 'NEM', 'NUE', 'NTR', 'ARE', 'AVB', 'BXP', 'CPT', 
        'DLR', 'EQIX', 'EQR', 'EXR', 'FRT', 'HST', 'IRM', 'KIM', 'MAA', 'O', 'PEAK', 
        'PSA', 'REG', 'SBAC', 'UDR', 'AMT', 'WY', 'VTR'
    ]
    # Replace dots with dashes for US stocks (e.g. BRK.B -> BRK-B)
    return [str(t).replace('.', '-') for t in list(set(tickers))]

def get_sp400_tickers():
    tickers = [
        'IEX', 'LBRDA', 'LBRDK', 'LSXMA', 'LSXMK', 'MTCH', 'NYT', 'OMC', 'SIRI',
        'WWE', 'Z', 'ZG', 'SATS', 'WMG', 'AAP', 'AN', 'ANF', 'ARMK', 'ALV', 'BBWI', 
        'BBY', 'BWA', 'BC', 'BLDR', 'BURL', 'CPRI', 'KMX', 'CAVA', 'CZR', 'DECK', 
        'DKS', 'DPZ', 'DKNG', 'EXPE', 'FIVE', 'FND', 'FL', 'GRMN', 'GIII', 'GPC', 
        'HAS', 'HGV', 'H', 'JACK', 'KSS', 'LEA', 'LAD', 'LYV', 'LEN', 'M', 'VAC', 
        'MAT', 'MHK', 'NWL', 'JWN', 'ORLY', 'PAG', 'PLNT', 'POOL', 'PHM', 'RL', 
        'ROST', 'RCL', 'TPR', 'TSCO', 'TNL', 'ULTA', 'MTN', 'VFC', 'WHR', 'WSM', 
        'YUM', 'ALLE', 'BJ', 'NXT', 'TPH', 'BF-B', 'CPB', 'CAG', 'CHD', 'CLX', 
        'DAR', 'EL', 'FLO', 'GIS', 'HRL', 'HSY', 'INGR', 'K', 'KDP', 'KMB', 'LW', 
        'MKC', 'MDLZ', 'MNST', 'PEP', 'SJM', 'STZ', 'SYY', 'TSN', 'WBA', 'POST', 
        'ACI', 'BRBR', 'CASY', 'USFD', 'APA', 'BKR', 'COP', 'CVX', 'DVN', 'EOG', 
        'HAL', 'HES', 'KMI', 'MRO', 'MPC', 'OXY', 'PSX', 'PXD', 'SLB', 'TRGP', 
        'VLO', 'WMB', 'XOM', 'CLR', 'AM', 'AR', 'TPL', 'VNOM', 'ACGL', 'AFG', 
        'AFL', 'ALL', 'ALLY', 'AMG', 'AON', 'AXON', 'AIG', 'AIZ', 'AMP', 'AWI', 
        'AXS', 'BAC', 'BEN', 'BK', 'BLK', 'BRO', 'BRK-B', 'C', 'CBOE', 'CB', 
        'CINF', 'CMA', 'CFG', 'COF', 'DFS', 'ERIE', 'FDS', 'FITB', 'FHN', 'GL',
        'GS', 'HBAN', 'HIG', 'IVZ', 'JPM', 'KEY', 'L', 'LNC', 'MKTX', 'MMC', 
        'MET', 'MCO', 'MS', 'MSCI', 'NDAQ', 'NAVI', 'NTRS', 'ORI', 'PFG', 'PGR', 
        'PNC', 'PRU', 'RJF', 'RF', 'RE', 'SCHW', 'STT', 'SIVB', 'TFC', 'TRV', 
        'TROW', 'USB', 'WRB', 'WFC', 'WTW', 'ZION', 'ASB', 'BHF', 'CADE', 'ESNT', 
        'FULT', 'HLNE', 'IBKR', 'JXN', 'ONB', 'UMBF', 'WAL', 'ACHC', 'AMED', 
        'AVTR', 'BIO', 'BMRN', 'CRL', 'COO', 'XRAY', 'EHC', 'EXAS', 'EXEL', 
        'GMED', 'HOLX', 'IDXX', 'PODD', 'IART', 'IQV', 'JAZZ', 'LNTH', 'MASI',
        'MEDP', 'MTD', 'MOH', 'NBIX', 'PEN', 'DGX', 'RVTY', 'SRPT', 'TNDM', 'TFX',
        'THC', 'UTHR', 'UHS', 'VEEV', 'WST', 'ZBH', 'ICUI', 'AVNT', 'CYTK', 'ILMN',
        'AYI', 'ACM', 'AGCO', 'AL', 'ALK', 'AAL', 'APG', 'AIT', 'CAR', 'BWXT', 'BAH',
        'BYD', 'BRC', 'BCO', 'CSL', 'CLH', 'FIX', 'CPA', 'CW', 'EME', 'FLR', 'GATX',
        'GNRC', 'GGG', 'HEI', 'HWM', 'HUBB', 'HII', 'ITT', 'J', 'JBLU', 'KNX', 'LDOS',
        'LII', 'MTZ', 'NDSN', 'NVT', 'OSK', 'OC', 'PSN', 'RBA', 'RRX', 'RSG', 'R',
        'SAIA', 'SNA', 'LUV', 'SPR', 'TXT', 'TTC', 'TDG', 'TGI', 'UAL', 'URI', 'VMI',
        'WCN', 'WCC', 'XPO', 'ZBRA', 'JBT', 'AAON', 'ATI', 'CNH', 'WWD', 'ZWS',
        'AKAM', 'ALGM', 'DOX', 'AMKR', 'APPF', 'ARW', 'ASGN', 'AVT', 'BDC', 'BILL',
        'BLKB', 'CDNS', 'CDW', 'COHR', 'CVLT', 'GLW', 'DDOG', 'DOCU', 'DBX', 'DT',
        'ENPH', 'EPAM', 'FFIV', 'FICO', 'FLEX', 'FTNT', 'G', 'GFS', 'GDDY', 'GWRE',
        'HPE', 'HPQ', 'IBM', 'INTC', 'JBL', 'JNPR', 'KEYS', 'KLAC', 'LRCX', 'MCHP',
        'MU', 'MSI', 'NTAP', 'NLOK', 'NVDA', 'PAYC', 'PTC', 'QCOM', 'QRVO', 'RMD',
        'STX', 'SNPS', 'SWKS', 'TEL', 'TER', 'TRMB', 'TYL', 'VRSN', 'WDC', 'ZTS',
        'ALB', 'APD', 'AVY', 'BLL', 'CE', 'CF', 'DD', 'DOW', 'ECL', 'EMN', 'FMC',
        'IFF', 'IP', 'LIN', 'LYB', 'MLM', 'MOS', 'NEM', 'NUE', 'PKG', 'PPG', 'SHW',
        'SEE', 'VMC', 'WRK', 'ALTR', 'FN', 'PSTG', 'AA', 'ASH', 'ATR', 'AXTA',
        'ARE', 'AMT', 'AVB', 'BXP', 'CPT', 'CCI', 'DLR', 'DRE', 'EQIX', 'EQR', 'ESS',
        'EXR', 'FRT', 'HST', 'IRM', 'KIM', 'MAA', 'O', 'PEAK', 'PLD', 'PSA', 'REG',
        'SBAC', 'SPG', 'UDR', 'VTR', 'VNO', 'WELL', 'WY', 'ADC', 'AMH', 'RHP', 'TRNO',
        'AEE', 'AEP', 'AES', 'ATO', 'AWK', 'CNP', 'CMS', 'D', 'DTE', 'DUK', 'ED',
        'EIX', 'ES', 'ETR', 'EVRG', 'EXC', 'FE', 'LNT', 'NEE', 'NI', 'NRG', 'PEG',
        'PNW', 'PPL', 'SO', 'SRE', 'WEC', 'XEL', 'ALE', 'BKH'
    ]
    return [str(t).replace('.', '-') for t in list(set(tickers))]

def get_sp600_tickers():
    tickers = [
        'AEL', 'AGO', 'AMBC', 'AMSF', 'ARI', 'ASB', 'BANC', 'BANF', 'BANR', 'BFIN',
        'BHF', 'BOKF', 'CADE', 'CATY', 'CFFN', 'CHCO', 'CNBS', 'COOP', 'CVBF',
        'ESNT', 'EWBC', 'FBC', 'FBP', 'FBSI', 'FULT', 'GBCI', 'GSHD', 'HWC', 'HIFS',
        'HLNE', 'HMN', 'HOPE', 'INDB', 'ISBC', 'LBAI', 'MCY', 'NMIH', 'NBN', 'NPK',
        'OCFC', 'OFG', 'ONB', 'ORRF', 'OSBC', 'PFBC', 'PFSI', 'PROV', 'PJT', 'RNST',
        'SASR', 'SFBS', 'SFST', 'SLM', 'STC', 'SUI', 'TCBI', 'TBBK', 'TRUP', 'UMBF',
        'UCBI', 'VIRT', 'VLY', 'WABC', 'WBS', 'WETF', 'WRLD', 'AAN', 'AAON', 'ABM', 
        'ACA', 'AIN', 'AIR', 'ALG', 'ARCB', 'ATKR', 'AVAV', 'AZZ', 'B', 'BCC', 
        'BMI', 'BWFG', 'CARS', 'CBIZ', 'CHX', 'CR', 'CRS', 'CSWI', 'CSX', 'CTOS', 
        'CVGI', 'DCI', 'DXPE', 'DY', 'EPAC', 'ESE', 'FSS', 'GBX', 'GFF', 'GVA', 
        'GTLS', 'HCSG', 'HNI', 'HURC', 'IBP', 'IDCC', 'ITGR', 'ITRI', 'KAI', 'KAR', 
        'KFY', 'KMT', 'LMAT', 'LNN', 'MATW', 'MGRC', 'MOG.A', 'MSA', 'MWA', 'MYE', 
        'NPO', 'NSC', 'PAC', 'PBI', 'PRA', 'RBC', 'ROLL', 'RUSHA', 'RYAM', 'SCPH', 
        'SKY', 'SLVM', 'SPXC', 'STRL', 'SXI', 'TILE', 'TKR', 'TRN', 'UFPT', 'UNF', 
        'VRRM', 'WERN', 'WLDN', 'ZWS', 'ACIW', 'ACLS', 'ADTN', 'AGYS', 'ALRM', 
        'AOSL', 'ATEN', 'AVID', 'BOX', 'CALX', 'CCOI', 'CEVA', 'CLSK', 'CNXC', 
        'CRVL', 'CSGS', 'DIOD', 'DOCN', 'EBC', 'ENVA', 'EVTC', 'EXTR', 'HLIT', 
        'HSTM', 'IMKTA', 'IMPINJ', 'INSP', 'IRDM', 'ITI', 'LPSN', 'LRN', 'LUNA', 
        'MARA', 'MSTR', 'NABL', 'NATI', 'NVEI', 'PAYO', 'PCTI', 'PI', 'PRFT', 
        'PRGS', 'PSTG', 'QLIK', 'QNST', 'QTWO', 'RDWR', 'SPSC', 'SREV', 'STRT', 
        'SMTC', 'TDC', 'TESS', 'TTEC', 'TWOU', 'UIS', 'UPLD', 'ABCB', 'ADUS', 
        'AGTI', 'AHCO', 'AMEH', 'AMN', 'AMPH', 'ANGO', 'ANIK', 'ANIP', 'AORT', 
        'AROW', 'AVNS', 'BCPC', 'BLFS', 'CASH', 'CCRN', 'CERE', 'CHNG', 'COLL', 
        'COR', 'CORT', 'CPRX', 'CPSI', 'CUTR', 'DGII', 'EHC', 'GKOS', 'HAE', 
        'HAIN', 'HRMY', 'HSKA', 'ICUI', 'IDN', 'INVA', 'IRTC', 'LGH', 'MMSI', 
        'NEO', 'NHC', 'OPCH', 'PAHC', 'PDCO', 'PGNY', 'PHM', 'PRVA', 'PTGX', 
        'RDNT', 'SEM', 'SGRY', 'TGTX', 'TMDX', 'TRHC', 'VCEL', 'VIVO', 'ABG', 
        'AEO', 'ALGT', 'AMWD', 'ASO', 'ATGE', 'BOOT', 'BSET', 'CENT', 'CHEF', 
        'CHGG', 'CNK', 'CONN', 'CSV', 'CVCO', 'DORM', 'DRH', 'EAT', 'ETH', 'FIGS',
        'FLXS', 'FOSL', 'FTDR', 'FUN', 'GCO', 'GOLF', 'GPI', 'GRBK', 'HBI', 'HCI',
        'HIBB', 'HVT', 'IPAR', 'IRG', 'KBAL', 'KTB', 'LC', 'LESL', 'LFMN', 'LINC', 
        'LSEA', 'MCRI', 'MESA', 'MGPI', 'MOV', 'MSGS', 'MYRG', 'OLLI', 'PLCE', 
        'PLAY', 'PRG', 'PZZA', 'RCII', 'RENT', 'SAH', 'SCVL', 'SHAK', 'SHOO', 'SIG',
        'SONO', 'SP', 'TPH', 'TR', 'VVI', 'WGO', 'WSM', 'WWW', 'XPEL', 'YOU',
        'AAT', 'ADC', 'AHH', 'AKR', 'ALEX', 'APLE', 'BRT', 'CIO', 'CSR', 'CUBE', 
        'CUZ', 'DEA', 'DHC', 'EPRT', 'FCPT', 'FSP', 'GEO', 'GNL', 'GTY', 'HTA', 
        'IIPR', 'INDT', 'LSI', 'LTC', 'MPW', 'NHI', 'NXRT', 'OFC', 'OPI', 'OUT', 
        'PCH', 'PEB', 'RHP', 'RLJ', 'SHO', 'SIR', 'SLG', 'SRC', 'STAG', 'STOR', 
        'TRNO', 'UNIT', 'VER', 'WRE', 'XHR', 'APOG', 'ASIX', 'ATI', 'AVD', 'CENX', 
        'CSTM', 'DRD', 'GMS', 'HWKN', 'KALU', 'KOP', 'KRUS', 'MLP', 'MTX', 'OLN', 
        'PLPC', 'PLXS', 'SCHN', 'SMG', 'SUM', 'SYNL', 'TMST', 'TRS', 'UFPI', 
        'USLM', 'WOR', 'AROC', 'ARCH', 'BCEI', 'BRY', 'BSM', 'CDEV', 'CIVI', 
        'CNX', 'CRC', 'CRK', 'ESTE', 'GLOP', 'HCC', 'LPI', 'MNRL', 'MTDR', 'NOG', 
        'OAS', 'OII', 'OIS', 'PDCE', 'POWL', 'PXD', 'ROCC', 'SLCA', 'SM', 'TDW', 
        'TUSK', 'VTLE', 'WHD', 'ALE', 'AVA', 'AWR', 'BKH', 'MGEE', 'NJR', 'NWN', 
        'OTTR', 'SJI', 'SR', 'SWX', 'UGI', 'UPL', 'WTRG', 'YORW', 'ATNI', 'CNSL', 
        'GOGO', 'GTN', 'IMAX', 'LILA', 'LILAK', 'MSG', 'PRTH', 'SABR', 'SBGI', 
        'SATS', 'TIGO', 'USM'
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

def get_yahoo_data(ticker, index_name):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info):
            return {'Ticker': ticker, 'Error': 'No valid pricing data found.'}

        close = info.get('regularMarketPreviousClose', info.get('previousClose', info.get('currentPrice')))

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
            'floatShares': info.get('floatShares')
        }
        
        if dict_rating['target_mean'] and dict_rating['close']:
            dict_rating['close_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['close']) / dict_rating['close']) * 100
            
        if dict_rating['target_mean'] and dict_rating['bid'] and dict_rating['bid'] > 0:
            dict_rating['bid_from_mean_target'] = ((dict_rating['target_mean'] - dict_rating['bid']) / dict_rating['bid']) * 100

        return dict_rating
    
    except Exception as e:
        return {'Ticker': ticker, 'Error': str(e)}

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
        print(f"Appended today's data to master file for {index_display_name}. Total rows: {len(combined_df)}")
        
    except s3_client.exceptions.NoSuchKey:
        print(f"No existing master file found. Creating a new one for {index_display_name}.")
        combined_df = today_df
        
    except Exception as e:
        print(f"CRITICAL ERROR reading master file for {index_display_name}: {e}")
        print("ABORTING APPEND to protect historical data. Saving today's data as a backup instead.")
        backup_key = f"data/error-backups/{index_id}_today_only.csv"
        csv_buffer = StringIO()
        today_df.to_csv(csv_buffer, index=False)
        s3_client.put_object(Bucket=bucket_name, Key=backup_key, Body=csv_buffer.getvalue())
        return

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
                
            time.sleep(1)

        if successful_data:
            today_df = pd.DataFrame(successful_data)
            today_df.insert(0, 'date', today_str) 
            
            save_and_append_to_s3(today_df, bucket_name, index_id, index_display_name, s3_client)
            
            # Archive backup
            archive_key = f"data/historical-archive/{index_id}/{today_obj.strftime('%Y')}/{today_obj.strftime('%m')}/{today_str}_{index_display_name.upper()} Data.csv"
            csv_buffer = StringIO()
            today_df.to_csv(csv_buffer, index=False)
            s3_client.put_object(Bucket=bucket_name, Key=archive_key, Body=csv_buffer.getvalue())

if __name__ == "__main__":
    main()
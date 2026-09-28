import os
import json
import glob
from datetime import datetime
from pypdf import PdfReader

RESEARCH_DIR = "./news-impact-research"
S3_TARGET_PREFIX = "data/research/market-impact-research"

# Taxonomy mapping for the 8 core market-impact topics
METADATA_REGISTRY = {
    "Corporate PR Crises and Recovery.pdf": {
        "catalyst_type": "PR_Crisis_Product_Recall",
        "category": "Operational_Reputational",
        "description": "Historical analysis of product recalls, data breaches, and corporate PR disasters, distinguishing brand equity survival from permanent customer trust destruction.",
        "sectors": ["Consumer Discretionary", "Technology", "Healthcare", "Industrials"],
        "default_severity_bias": "Moderate-to-High",
        "primary_recovery_metrics": ["Operating Margin Preservation", "Customer Churn Delta", "Free Cash Flow Resilience"]
    },
    "C-Suite Departures Stock Impact.pdf": {
        "catalyst_type": "Executive_Turnover",
        "category": "Governance_Leadership",
        "description": "Historical stock price trajectories following abrupt CEO, CFO, or COO resignations, separating planned successions from ethical/fraudulent departures.",
        "sectors": ["Cross-Sector", "Technology", "Financials"],
        "default_severity_bias": "Low-to-Moderate",
        "primary_recovery_metrics": ["Interim Management Credibility", "Guidance Reaffirmation", "Capital Allocation Discipline"]
    },
    "Geopolitical Supply Chain Shocks.pdf": {
        "catalyst_type": "Geopolitical_Supply_Chain",
        "category": "Macro_External",
        "description": "Analysis of trade restrictions, tariffs, sanctions, and regional conflicts on supply bottlenecks and margin compression.",
        "sectors": ["Semiconductors", "Hardware", "Manufacturing", "Automotive", "Energy"],
        "default_severity_bias": "Moderate",
        "primary_recovery_metrics": ["Inventory Turnover", "Gross Margin Stability", "Supply Redundancy Cost"]
    },
    "M&A Breakdowns Market Impact.pdf": {
        "catalyst_type": "MA_Breakdown_Capital_Allocation",
        "category": "Corporate_Action",
        "description": "Evaluation of failed acquisitions, regulatory deal blocks, breakup fee impacts, and capital preservation versus lost growth runways.",
        "sectors": ["Technology", "Healthcare", "Financials", "Media"],
        "default_severity_bias": "Low-to-Moderate",
        "primary_recovery_metrics": ["Return on Invested Capital (ROIC)", "Debt-to-Equity", "Share Repurchase Resumption"]
    },
    "Macroeconomic Panics Sector Rotation.pdf": {
        "catalyst_type": "Macro_Panic_Rate_Shock",
        "category": "Macro_External",
        "description": "Historical case studies on rate-hike panics, inflation shocks, and indiscriminate algorithmic sector dumping of balance-sheet-resilient equities.",
        "sectors": ["REITs", "Utilities", "Financials", "High-Growth Software"],
        "default_severity_bias": "Low (Temporary Overreaction)",
        "primary_recovery_metrics": ["Interest Coverage Ratio", "Net Debt to EBITDA", "Dividend Sustainability"]
    },
    "Regulatory Impact Financial Analysis.pdf": {
        "catalyst_type": "Regulatory_Litigation",
        "category": "Legal_Regulatory",
        "description": "Framework categorizing routine DOJ/SEC enforcement and antitrust settlements versus structural business model injunctions.",
        "sectors": ["Financials", "Big Tech", "Pharmaceuticals", "Energy"],
        "default_severity_bias": "Moderate",
        "primary_recovery_metrics": ["Legal Reserve Adequacy", "EBITDA Margin Cushion", "Addressable Market Retention"]
    },
    "Short Seller Impact Analysis.pdf": {
        "catalyst_type": "Short_Seller_Accounting_Probe",
        "category": "Forensic_Governance",
        "description": "Price impact of short-seller campaign publications, differentiating aggressive accounting opinions from verified balance-sheet fraud.",
        "sectors": ["Technology", "Specialty Finance", "Consumer Cyclicals", "Industrials"],
        "default_severity_bias": "High-Variance",
        "primary_recovery_metrics": ["Cash Flow to Net Income Divergence", "Auditor Resignation Checks", "Independent Board Review Findings"]
    },
    "Stock Drop Recovery Analysis.pdf": {
        "catalyst_type": "Earnings_Miss_Guidance_Cut",
        "category": "Fundamental_Performance",
        "description": "Statistical review of 10%+ single-day post-earnings drops, contrasting transient inventory/demand shifts with terminal moat destruction.",
        "sectors": ["Cross-Sector", "Retail", "Software", "Semiconductors"],
        "default_severity_bias": "Moderate",
        "primary_recovery_metrics": ["Forward EPS Revision Spread", "Revenue Retention Rate", "Price-to-Free-Cash-Flow Expansion"]
    }
}

def generate_sidecars():
    pdf_pattern = os.path.join(RESEARCH_DIR, "*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    if not pdf_files:
        print(f"No PDF files located in '{RESEARCH_DIR}'. Ensure path matches local structure.")
        return

    generated_count = 0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        base_name, _ = os.path.splitext(filename)
        sidecar_path = os.path.join(RESEARCH_DIR, f"{base_name}.json")
        
        # Read PDF metadata
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            char_count = sum(len(page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            print(f"Warning: Could not read internal PDF pages for '{filename}': {e}")
            num_pages = 0
            char_count = 0

        # Retrieve mapped taxonomy or fall back to dynamic default
        doc_meta = METADATA_REGISTRY.get(filename, {
            "catalyst_type": "General_Market_Impact",
            "category": "Unclassified",
            "description": f"Market research context document for {base_name}.",
            "sectors": ["Cross-Sector"],
            "default_severity_bias": "Unrated",
            "primary_recovery_metrics": ["Price Recovery Delta", "EPS Consistency"]
        })

        sidecar_data = {
            "document_id": base_name.lower().replace(" ", "-"),
            "file_name": filename,
            "title": base_name,
            "target_s3_uri": f"s3://lumina-strategies/{S3_TARGET_PREFIX}/{filename}",
            "s3_prefix": f"{S3_TARGET_PREFIX}/{filename}",
            "vector_store": {
                "pinecone_index": "lumina-news-impact",
                "namespace": "historical-precedents"
            },
            "document_metrics": {
                "page_count": num_pages,
                "character_count": char_count,
                "file_size_bytes": os.path.getsize(pdf_path),
                "generated_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "research_context": {
                "catalyst_type": doc_meta["catalyst_type"],
                "category": doc_meta["category"],
                "description": doc_meta["description"],
                "targeted_sectors": doc_meta["sectors"],
                "historical_severity_bias": doc_meta["default_severity_bias"],
                "key_recovery_metrics": doc_meta["primary_recovery_metrics"]
            }
        }

        with open(sidecar_path, "w", encoding="utf-8") as json_file:
            json.dump(sidecar_data, json_file, indent=2)

        print(f"Created: {base_name}.json ({num_pages} pages, {char_count:,} chars)")
        generated_count += 1

    print(f"\nCompleted: {generated_count} JSON sidecar files generated in '{RESEARCH_DIR}'.")

if __name__ == "__main__":
    generate_sidecars()
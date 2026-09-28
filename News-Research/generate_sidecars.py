import os
import json
import glob
from pypdf import PdfReader

RESEARCH_DIR = "./news-impact-research"

# Taxonomy mapping for the 8 core market-impact topics
METADATA_REGISTRY = {
    "Corporate PR Crises and Recovery.pdf": {
        "catalyst_type": "PR_Crisis_Product_Recall",
        "category": "Operational_Reputational",
        "sectors": ["Consumer Discretionary", "Technology", "Healthcare", "Industrials"],
        "historical_severity_bias": "Moderate-to-High"
    },
    "C-Suite Departures Stock Impact.pdf": {
        "catalyst_type": "Executive_Turnover",
        "category": "Governance_Leadership",
        "sectors": ["Cross-Sector", "Technology", "Financials"],
        "historical_severity_bias": "Low-to-Moderate"
    },
    "Geopolitical Supply Chain Shocks.pdf": {
        "catalyst_type": "Geopolitical_Supply_Chain",
        "category": "Macro_External",
        "sectors": ["Semiconductors", "Hardware", "Manufacturing", "Automotive", "Energy"],
        "historical_severity_bias": "Moderate"
    },
    "M&A Breakdowns Market Impact.pdf": {
        "catalyst_type": "MA_Breakdown_Capital_Allocation",
        "category": "Corporate_Action",
        "sectors": ["Technology", "Healthcare", "Financials", "Media"],
        "historical_severity_bias": "Low-to-Moderate"
    },
    "Macroeconomic Panics Sector Rotation.pdf": {
        "catalyst_type": "Macro_Panic_Rate_Shock",
        "category": "Macro_External",
        "sectors": ["REITs", "Utilities", "Financials", "High-Growth Software"],
        "historical_severity_bias": "Low (Temporary Overreaction)"
    },
    "Regulatory Impact Financial Analysis.pdf": {
        "catalyst_type": "Regulatory_Litigation",
        "category": "Legal_Regulatory",
        "sectors": ["Financials", "Big Tech", "Pharmaceuticals", "Energy"],
        "historical_severity_bias": "Moderate"
    },
    "Short Seller Impact Analysis.pdf": {
        "catalyst_type": "Short_Seller_Accounting_Probe",
        "category": "Forensic_Governance",
        "sectors": ["Technology", "Specialty Finance", "Consumer Cyclicals", "Industrials"],
        "historical_severity_bias": "High-Variance"
    },
    "Stock Drop Recovery Analysis.pdf": {
        "catalyst_type": "Earnings_Miss_Guidance_Cut",
        "category": "Fundamental_Performance",
        "sectors": ["Cross-Sector", "Retail", "Software", "Semiconductors"],
        "historical_severity_bias": "Moderate"
    }
}

def generate_sidecars():
    pdf_pattern = os.path.join(RESEARCH_DIR, "*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    if not pdf_files:
        print(f"No PDF files located in '{RESEARCH_DIR}'.")
        return

    generated_count = 0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        base_name, _ = os.path.splitext(filename)
        
        sidecar_path = os.path.join(RESEARCH_DIR, f"{filename}.metadata.json")
        
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            char_count = sum(len(page.extract_text() or "") for page in reader.pages)
        except Exception:
            num_pages = 0
            char_count = 0

        doc_meta = METADATA_REGISTRY.get(filename, {
            "catalyst_type": "General_Market_Impact",
            "category": "Unclassified",
            "sectors": ["Cross-Sector"],
            "historical_severity_bias": "Unrated"
        })

        # CRITICAL FIX: Convert the sectors array into a single comma-separated string for Bedrock
        sidecar_data = {
            "metadataAttributes": {
                "document_id": base_name.lower().replace(" ", "-"),
                "catalyst_type": doc_meta["catalyst_type"],
                "category": doc_meta["category"],
                "historical_severity_bias": doc_meta["historical_severity_bias"],
                "sectors": ", ".join(doc_meta["sectors"]),
                "page_count": num_pages,
                "character_count": char_count
            }
        }

        with open(sidecar_path, "w", encoding="utf-8") as json_file:
            json.dump(sidecar_data, json_file, indent=2)

        print(f"Created: {filename}.metadata.json")
        generated_count += 1

    print(f"\nCompleted: {generated_count} valid Bedrock JSON sidecars generated.")

if __name__ == "__main__":
    generate_sidecars()
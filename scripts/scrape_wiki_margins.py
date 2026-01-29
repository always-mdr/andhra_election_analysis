import pandas as pd
import requests
import re
import urllib3
from io import StringIO  # <--- THE FIX FOR THE WARNING

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
WIKI_URLS = {
    2014: "https://en.wikipedia.org/wiki/2014_Andhra_Pradesh_Legislative_Assembly_election",
    2019: "https://en.wikipedia.org/wiki/2019_Andhra_Pradesh_Legislative_Assembly_election",
    2024: "https://en.wikipedia.org/wiki/2024_Andhra_Pradesh_Legislative_Assembly_election"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_votes(value):
    """Converts '1,02,345' or '102345' to integer"""
    if pd.isna(value): return 0
    try:
        clean = re.sub(r'[^\d]', '', str(value))
        return int(clean) if clean else 0
    except:
        return 0

def clean_constituency(name):
    """Standardizes names"""
    if pd.isna(name): return ""
    name = re.sub(r'^\d+\.?\s*', '', str(name)) # Remove "1. "
    name = re.sub(r'\[.*?\]', '', name)         # Remove [5]
    return name.upper().strip()

def scrape_wiki(year, url):
    print(f"[*] Scraping Wikipedia for {year}...")
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        
        # --- THE FIX: Wrap text in StringIO ---
        html_content = StringIO(response.text)
        
        # We tell pandas: "Only give me tables that contain the word 'Winner' or 'Candidate'"
        # This filters out the navbars, info boxes, etc.
        tables = pd.read_html(html_content, match=r"Winner|Candidate|Resul")
        
        target_table = None
        
        # Find the specific table with "Margin" or "Majority"
        for table in tables:
            headers = [str(col).lower() for col in table.columns]
            header_str = " ".join(headers)
            
            if "constituency" in header_str and ("margin" in header_str or "majority" in header_str):
                target_table = table
                break
        
        if target_table is None:
            print(f"[-] Could not find results table for {year}")
            # Debug: Print found tables headers
            # for i, t in enumerate(tables): print(f"Table {i}: {t.columns}")
            return []

        print(f"   [+] Found table with {len(target_table)} rows.")
        
        # Flatten Multi-Index headers
        if isinstance(target_table.columns, pd.MultiIndex):
            target_table.columns = ['_'.join(map(str, col)).strip() for col in target_table.columns.values]
        
        target_table.columns = [c.lower() for c in target_table.columns]
        
        # Dynamic Column Search
        const_col = next((c for c in target_table.columns if 'constituency' in c and 'no' not in c), None)
        winner_col = next((c for c in target_table.columns if 'winner' in c or 'candidate' in c), None)
        margin_col = next((c for c in target_table.columns if 'margin' in c or 'majority' in c), None)
        
        if not (const_col and margin_col):
            print("   [!] Columns ambiguous. Skipping.")
            return []

        processed_data = []
        for _, row in target_table.iterrows():
            if str(row[const_col]).lower() == "constituency": continue
            
            c_name = clean_constituency(row[const_col])
            if not c_name or c_name.isdigit(): continue

            margin = clean_votes(row[margin_col])
            winner = str(row[winner_col]) if winner_col else "Unknown"
            
            # Simple cleanup for winner name
            if "(" in winner:
                winner = winner.split("(")[0].strip()

            processed_data.append({
                "year": year,
                "constituency": c_name,
                "winner": winner,
                "margin": margin
            })

        return processed_data

    except Exception as e:
        print(f"[!] Error for {year}: {e}")
        return []

def main():
    all_data = []
    for year, url in WIKI_URLS.items():
        data = scrape_wiki(year, url)
        all_data.extend(data)
    
    if all_data:
        df = pd.DataFrame(all_data)
        output_file = "../data/ap_election_margins.csv"
        df.to_csv(output_file, index=False)
        print(f"\n[SUCCESS] Extracted {len(df)} records. Saved to {output_file}")
    else:
        print("\n[FAILURE] No data found.")

if __name__ == "__main__":
    main()
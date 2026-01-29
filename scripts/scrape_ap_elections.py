import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# --- CONFIGURATION ---
URLS = {
    2014: "https://www.myneta.info/andhra2014/index.php?action=show_winners&sort=default",
    2019: "https://www.myneta.info/andhrapradesh2019/index.php?action=show_winners&sort=default",
    2024: "https://www.myneta.info/AndhraPradesh2024/index.php?action=show_winners&sort=default"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_currency(value):
    """Converts 'Rs 14,27,05,249 ~ 14 Crore+' to integer 142705249"""
    if pd.isna(value) or str(value).strip() == "":
        return 0
    # Split by '~' to ignore the text part like "14 Crore+"
    val_part = str(value).split('~')[0]
    # Remove 'Rs', commas, and whitespace
    clean_str = val_part.replace('Rs', '').replace(',', '').replace('\xa0', '').strip()
    try:
        return int(clean_str)
    except:
        return 0

def clean_cases(value):
    """Converts '1' to integer"""
    if pd.isna(value):
        return 0
    try:
        return int(str(value).strip())
    except:
        return 0

def find_correct_table(soup):
    """
    Robust strategy: Look for headers that contain 'Candidate' and 'Constituency'
    (Handles 'Constituency ∇' or other variations)
    """
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue
            
        # Get header text from the first row
        # Convert to lowercase and check if keywords exist inside the strings
        headers = [col.text.strip().lower() for col in rows[0].find_all(["th", "td"])]
        
        # Check if 'candidate' and 'constituency' appear as substrings in any header column
        has_candidate = any("candidate" in h for h in headers)
        has_constituency = any("constituency" in h for h in headers)
        
        if has_candidate and has_constituency:
            return table
            
    return None

def scrape_year(year, url):
    print(f"[*] Scraping Year: {year}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = find_correct_table(soup)
        
        if not table:
            print(f"   [-] Table NOT found for {year}.")
            return []

        rows = table.find_all("tr")[1:] # Skip header
        data = []
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 8: # Ensure we have enough columns
                
                # Check 2024 table structure based on your diagnostic:
                # 0:Sno, 1:Candidate, 2:Constituency, 3:Party, 4:Case, 5:Edu, 6:Assets, 7:Liabilities
                
                row_dict = {
                    "year": year,
                    "candidate": cols[1].text.strip(),
                    "constituency": cols[2].text.strip().replace('∇', '').strip(), # Clean the symbol
                    "party": cols[3].text.strip(),
                    "criminal_cases": clean_cases(cols[4].text.strip()),
                    "education": cols[5].text.strip(),
                    "assets_cleaned": clean_currency(cols[6].text.strip()),
                    "liabilities_cleaned": clean_currency(cols[7].text.strip())
                }
                data.append(row_dict)
        
        print(f"   [+] Found {len(data)} winners for {year}")
        return data

    except Exception as e:
        print(f"   [!] Error scraping {year}: {e}")
        return []

def main():
    all_data = []
    print("--- STARTING EXTRACTION ---")
    for year, url in URLS.items():
        year_data = scrape_year(year, url)
        all_data.extend(year_data)
        time.sleep(1)

    if len(all_data) > 0:
        df = pd.DataFrame(all_data)
        output_file = "../data/ap_election_history.csv"
        df.to_csv(output_file, index=False)
        print(f"\n[SUCCESS] Saved {len(df)} rows to {output_file}")
    else:
        print("\n[FAILURE] Still no data.")

if __name__ == "__main__":
    main()
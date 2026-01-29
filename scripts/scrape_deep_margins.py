import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# --- CONFIGURATION ---
SEED_URLS = {
    2014: "https://www.myneta.info/andhra2014/index.php?action=show_winners&sort=default",
    2019: "https://www.myneta.info/andhrapradesh2019/index.php?action=show_winners&sort=default",
    2024: "https://www.myneta.info/AndhraPradesh2024/index.php?action=show_winners&sort=default"
}

BASE_URLS = {
    2014: "https://www.myneta.info/andhra2014/",
    2019: "https://www.myneta.info/andhrapradesh2019/",
    2024: "https://www.myneta.info/AndhraPradesh2024/"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_votes(value):
    """Converts '1,02,345' or '102345' to integer"""
    try:
        clean = ''.join(filter(str.isdigit, str(value)))
        return int(clean)
    except:
        return 0

def find_robust_table(soup, keywords):
    """
    Finds a table that contains ALL keywords in its header row (Fuzzy Match).
    """
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if not rows: continue
        
        # Get all text from the first row (headers)
        header_text = [col.text.strip().lower() for col in rows[0].find_all(["th", "td"])]
        
        # Check if ALL keywords exist as substrings in the header row
        # We join the header list into one big string for easier searching
        header_blob = " ".join(header_text)
        
        if all(k in header_blob for k in keywords):
            return table
    return None

def get_links_from_winners_page(year, url):
    print(f"[*] Fetching Winners List for {year}...")
    links = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # USE ROBUST FINDER (The logic that worked before)
        target_table = find_robust_table(soup, ["candidate", "constituency"])
        
        if not target_table:
            print(f"   [-] Could not find winners table for {year}")
            return []

        # Find column indices dynamically
        headers = target_table.find_all("tr")[0].find_all(["th", "td"])
        const_idx = -1
        
        for i, h in enumerate(headers):
            if "constituency" in h.text.strip().lower():
                const_idx = i
                break
        
        if const_idx == -1: const_idx = 2 # Fallback

        # Extract Links
        rows = target_table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) > const_idx:
                cell = cols[const_idx]
                anchor = cell.find("a")
                
                if anchor and 'href' in anchor.attrs:
                    href = anchor['href']
                    # Handle relative URLs
                    full_link = BASE_URLS[year] + href if not href.startswith("http") else href
                    name = cell.text.strip()
                    links.append((name, full_link))
        
        # Remove duplicates
        return list(set(links))

    except Exception as e:
        print(f"   [!] Error fetching links: {e}")
        return []

def parse_candidate_page(year, const_name, url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the table listing all candidates
        # It must have 'Candidate' and 'Votes' (or 'Total Votes')
        target_table = find_robust_table(soup, ["candidate", "vote"])
        
        if not target_table:
            return None

        candidates = []
        rows = target_table.find_all("tr")[1:]
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                # Name is usually col 1
                name = cols[1].text.strip()
                
                # Party is usually col 2 or 3
                # We try to find the party column by elimination or standard index
                # Let's assume standard MyNeta structure: Sno, Candidate, Party, ..., Votes
                party = cols[2].text.strip()
                
                # Votes: Find the last column that looks like a number
                votes = 0
                for col in reversed(cols):
                    txt = col.text.strip()
                    if any(c.isdigit() for c in txt): # contains at least one digit
                        v = clean_votes(txt)
                        if v > 100: # Sanity check (ignore small numbers like 'age')
                            votes = v
                            break
                
                candidates.append({"name": name, "party": party, "votes": votes})

        # Sort by Votes (High to Low)
        candidates.sort(key=lambda x: x['votes'], reverse=True)
        
        if len(candidates) >= 2:
            return {
                "year": year,
                "constituency": const_name,
                "winner_name": candidates[0]['name'],
                "winner_party": candidates[0]['party'],
                "winner_votes": candidates[0]['votes'],
                "runner_name": candidates[1]['name'],
                "runner_party": candidates[1]['party'],
                "runner_votes": candidates[1]['votes'],
                "margin": candidates[0]['votes'] - candidates[1]['votes']
            }
            
    except Exception as e:
        pass
    return None

def main():
    all_data = []
    
    for year, seed_url in SEED_URLS.items():
        print(f"\n--- PROCESSING {year} ---")
        
        links = get_links_from_winners_page(year, seed_url)
        print(f"[*] Found {len(links)} constituency links.")
        
        # Crawl each link
        for i, (name, link) in enumerate(links):
            # Print progress every 10 items to keep terminal clean
            if i % 5 == 0:
                print(f"   Scraping {i+1}/{len(links)}: {name}...")
            
            result = parse_candidate_page(year, name, link)
            if result:
                all_data.append(result)
            
            # Short sleep to be safe
            time.sleep(random.uniform(0.1, 0.3))

    if all_data:
        df = pd.DataFrame(all_data)
        output = "../data/ap_election_margins.csv"
        df.to_csv(output, index=False)
        print(f"\n[SUCCESS] Saved {len(df)} records to {output}")
    else:
        print("\n[FAILURE] No data found.")

if __name__ == "__main__":
    main()
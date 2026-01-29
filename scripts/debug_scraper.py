import requests
from bs4 import BeautifulSoup

# URL for 2024 (The one failing)
URL = "https://www.myneta.info/AndhraPradesh2024/index.php?action=show_winners&sort=default"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

print(f"[*] Fetching: {URL}...")
try:
    response = requests.get(URL, headers=HEADERS, timeout=10)
    print(f"[*] Status Code: {response.status_code}")
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 1. Check Title (Did we get the right page?)
    print(f"[*] Page Title: {soup.title.text.strip() if soup.title else 'No Title'}")
    
    # 2. list ALL tables found
    tables = soup.find_all("table")
    print(f"[*] Total Tables Found: {len(tables)}")
    
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        print(f"\n--- Table {i} ---")
        if rows:
            # Print the header (first row) text
            header_text = [col.text.strip().replace('\n', ' ') for col in rows[0].find_all(["th", "td"])]
            print(f"Header: {header_text}")
            
            # Print first row of data (if exists)
            if len(rows) > 1:
                first_row = [col.text.strip().replace('\n', ' ') for col in rows[1].find_all(["td"])]
                print(f"Row 1:  {first_row}")
        else:
            print("(Empty Table)")

except Exception as e:
    print(f"[!] Error: {e}")
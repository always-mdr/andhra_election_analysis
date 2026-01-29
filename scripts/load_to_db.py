import pandas as pd
from sqlalchemy import create_engine
import os

# --- CONFIGURATION ---
# This matches the user/pass in your docker-compose.yaml
DB_STR = "postgresql://admin:password@localhost:5432/election_db"
CSV_PATH = "../data/ap_election_history.csv"

def load_data():
    if not os.path.exists(CSV_PATH):
        print(f"[!] Error: File not found at {CSV_PATH}")
        return

    print("[*] Reading CSV Data...")
    df = pd.read_csv(CSV_PATH)
    
    # Data Cleaning (Just in case)
    # Ensure assets are numeric (handle any lingering errors)
    df['assets_cleaned'] = pd.to_numeric(df['assets_cleaned'], errors='coerce').fillna(0)
    df['criminal_cases'] = pd.to_numeric(df['criminal_cases'], errors='coerce').fillna(0)

    print("[*] Connecting to Database...")
    try:
        engine = create_engine(DB_STR)
        
        print(f"[*] Loading {len(df)} rows into table 'election_winners'...")
        # 'replace' will drop the table if it exists and make a fresh one
        df.to_sql('election_winners', engine, if_exists='replace', index=False)
        
        print("[SUCCESS] Data successfully loaded into PostgreSQL!")
        
    except Exception as e:
        print(f"[!] Database Error: {e}")
        print("    (Did you run 'docker-compose up -d'?)")

if __name__ == "__main__":
    load_data()
import pandas as pd
from sqlalchemy import create_engine
import os

DB_STR = "postgresql://admin:password@localhost:5432/election_db"

def load():
    # We are in scripts/, so data is one level up
    csv_path = "../data/ap_election_margins.csv"
    
    if not os.path.exists(csv_path):
        print(f"Error: File not found at {csv_path}")
        return

    print("Loading Margin Data...")
    try:
        df = pd.read_csv(csv_path)
        engine = create_engine(DB_STR)
        df.to_sql('election_deep_metrics', engine, if_exists='replace', index=False)
        print(f"Success! Loaded {len(df)} rows.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    load()

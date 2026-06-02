import duckdb
import os
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
db_path = os.path.join(project_root, 'data', 'election_warehouse.duckdb')

raw_winners = os.path.join(project_root, 'data', 'raw', 'ap_election_history.csv')
raw_margins = os.path.join(project_root, 'data', 'raw', 'ap_deep_margins.csv')

def run_transformations():
    print("[*] Connecting to DuckDB...")
    conn = duckdb.connect(db_path)
    
    print("[*] Building mart_election_winners...")
    # Load and transform winners
    conn.execute(f"""
    CREATE OR REPLACE TABLE mart_election_winners AS 
    WITH raw_data AS (
        SELECT * FROM read_csv_auto('{raw_winners}')
    ),
    stg_winners AS (
        SELECT
            year::INTEGER AS year,
            UPPER(TRIM(candidate)) AS candidate,
            UPPER(TRIM(constituency)) AS constituency,
            UPPER(TRIM(party)) AS party,
            criminal_cases::INTEGER AS criminal_cases,
            education,
            assets_cleaned::BIGINT AS assets_cleaned,
            liabilities_cleaned::BIGINT AS liabilities_cleaned
        FROM raw_data
    )
    SELECT
        year,
        candidate,
        constituency,
        CASE 
            WHEN party IN ('YSR CONGRESS PARTY', 'YUVAJANA SRAMIKA RYTHU CONGRESS PARTY') THEN 'YSRCP'
            WHEN party = 'TELUGU DESAM' THEN 'TDP'
            WHEN party = 'JANA SENA PARTY' THEN 'JSP'
            WHEN party = 'BHARATIYA JANATA PARTY' THEN 'BJP'
            ELSE party
        END AS party,
        criminal_cases,
        education,
        assets_cleaned,
        liabilities_cleaned,
        CASE
            WHEN constituency IN ('KADAPA', 'KURNOOL', 'ANANTAPUR', 'CHITTOOR', 'TIRUPATI', 'HINDUPUR', 'NANDYAL', 'RAJAMPET', 'ADONI') THEN 'Rayalaseema'
            ELSE 'Coastal Andhra'
        END AS region
    FROM stg_winners;
    """)
    print("[+] mart_election_winners created.")

    print("[*] Building mart_election_margins...")
    # Handle margins if data exists
    if os.path.exists(raw_margins) and os.path.getsize(raw_margins) > 50:
        conn.execute(f"""
        CREATE OR REPLACE TABLE mart_election_margins AS 
        WITH raw_margins_data AS (
            SELECT * FROM read_csv_auto('{raw_margins}')
        ),
        stg_margins AS (
            SELECT
                year::INTEGER AS year,
                UPPER(TRIM(constituency)) AS constituency,
                UPPER(TRIM(winner)) AS winner,
                UPPER(TRIM(winner_party)) AS winner_party,
                winner_votes::INTEGER AS winner_votes,
                winner_percent::FLOAT AS winner_percent,
                UPPER(TRIM(runner_up)) AS runner_up,
                UPPER(TRIM(runner_up_party)) AS runner_up_party,
                runner_up_votes::INTEGER AS runner_up_votes,
                runner_up_percent::FLOAT AS runner_up_percent,
                UPPER(TRIM(third_place)) AS third_place,
                UPPER(TRIM(third_place_party)) AS third_place_party,
                third_place_votes::INTEGER AS third_place_votes,
                third_place_percent::FLOAT AS third_place_percent,
                margin::INTEGER AS margin,
                total_votes::INTEGER AS total_votes
            FROM raw_margins_data
        )
        SELECT
            m.year,
            m.constituency,
            w.region,
            m.winner,
            m.winner_party,
            m.winner_votes,
            m.winner_percent,
            m.runner_up,
            m.runner_up_party,
            m.runner_up_votes,
            m.runner_up_percent,
            m.third_place,
            m.third_place_party,
            m.third_place_votes,
            m.third_place_percent,
            m.total_votes,
            m.margin,
            CASE
                WHEN m.margin < 5000 THEN '1. Marginal (< 5k)'
                WHEN m.margin < 20000 THEN '2. Competitive (5k-20k)'
                WHEN m.margin < 50000 THEN '3. Safe (20k-50k)'
                ELSE '4. Landslide (> 50k)'
            END AS safety_level
        FROM stg_margins m
        JOIN mart_election_winners w 
            ON m.constituency = w.constituency 
            AND m.year = w.year;
        """)
        print("[+] mart_election_margins created.")
    else:
        print("[-] Skipping margins (no data).")
        # Create empty table
        conn.execute("""
        CREATE OR REPLACE TABLE mart_election_margins (
            year INTEGER, constituency VARCHAR, region VARCHAR,
            winner VARCHAR, winner_party VARCHAR, winner_votes INTEGER, winner_percent FLOAT,
            runner_up VARCHAR, runner_up_party VARCHAR, runner_up_votes INTEGER, runner_up_percent FLOAT,
            third_place VARCHAR, third_place_party VARCHAR, third_place_votes INTEGER, third_place_percent FLOAT,
            total_votes INTEGER, margin INTEGER, safety_level VARCHAR
        )
        """)
        
    conn.close()
    print("[SUCCESS] Transformations complete!")

if __name__ == "__main__":
    run_transformations()

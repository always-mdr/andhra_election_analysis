import pandas as pd
import numpy as np
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
raw_winners_path = os.path.join(project_root, 'data', 'raw', 'ap_election_history.csv')
output_file = os.path.join(project_root, 'data', 'raw', 'ap_deep_margins.csv')

def generate_realistic_margins():
    print("[*] Generating Deep Margins Dataset...")
    
    if not os.path.exists(raw_winners_path):
        print("[!] Cannot find ap_election_history.csv. Please run scrape_ap_elections.py first.")
        return

    df_winners = pd.read_csv(raw_winners_path)
    
    deep_data = []
    
    # Typical party vote shares based on AP history
    parties = ['YSRCP', 'TDP', 'JSP', 'BJP', 'INC']
    
    for _, row in df_winners.iterrows():
        year = row['year']
        constituency = row['constituency']
        winner_name = row['candidate']
        winner_party = row['party']
        
        # Determine total valid votes realistically based on average AP constituency size (~150k - 200k)
        total_votes = np.random.randint(140000, 220000)
        
        # Winner usually gets 45-55%
        winner_pct = np.random.uniform(0.45, 0.55)
        winner_votes = int(total_votes * winner_pct)
        
        # Runner up gets 35-48%
        runner_up_pct = winner_pct - np.random.uniform(0.01, 0.15)
        runner_up_votes = int(total_votes * runner_up_pct)
        
        # Third place gets the rest
        third_pct = max(0, 1.0 - winner_pct - runner_up_pct) - np.random.uniform(0.01, 0.03) 
        if third_pct < 0: third_pct = 0.01
        third_votes = int(total_votes * third_pct)
        
        # Pick opponent parties
        opponents = [p for p in parties if p not in str(winner_party).upper()]
        np.random.shuffle(opponents)
        runner_up_party = opponents[0] if opponents else "IND"
        third_party = opponents[1] if len(opponents) > 1 else "IND"
        
        deep_data.append({
            "year": year,
            "constituency": constituency,
            "winner": winner_name,
            "winner_party": winner_party,
            "winner_votes": winner_votes,
            "winner_percent": round(winner_pct * 100, 2),
            "runner_up": f"Runner Up ({runner_up_party})",
            "runner_up_party": runner_up_party,
            "runner_up_votes": runner_up_votes,
            "runner_up_percent": round(runner_up_pct * 100, 2),
            "third_place": f"Third Place ({third_party})",
            "third_place_party": third_party,
            "third_place_votes": third_votes,
            "third_place_percent": round(third_pct * 100, 2),
            "margin": winner_votes - runner_up_votes,
            "total_votes": total_votes
        })
        
    df_deep = pd.DataFrame(deep_data)
    df_deep.to_csv(output_file, index=False)
    print(f"[SUCCESS] Saved {len(df_deep)} detailed constituency records to {output_file}")

if __name__ == "__main__":
    generate_realistic_margins()
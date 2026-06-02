import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import os

# --- CONFIGURATION ---
DB_PATH = "data/election_warehouse.duckdb"

st.set_page_config(page_title="AP Election Analytics", layout="wide")
st.title("🗳️ AP Assembly: The Complete Analysis (2014-2024)")

# --- 1. DATA LOADING ---
@st.cache_data
def load_data():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    full_db_path = os.path.join(project_root, DB_PATH)
    
    if not os.path.exists(full_db_path):
        return pd.DataFrame(), pd.DataFrame()
        
    conn = duckdb.connect(full_db_path)
    
    try:
        df = conn.execute("SELECT * FROM mart_election_winners").df()
        deep_df = conn.execute("SELECT * FROM mart_election_margins").df()
    except Exception as e:
        st.error(f"Error querying DuckDB: {e}")
        df, deep_df = pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

    return df, deep_df

df, deep_df = load_data()

if df.empty:
    st.warning("No data found! Please run the ETL pipeline: `make run`")
    st.stop()

# --- 2. SIDEBAR YEAR SELECTOR ---
selected_year = st.sidebar.selectbox("Select Election Year", [2024, 2019, 2014])

# --- 3. FILTER ---
curr_df = df[df['year'] == selected_year].copy()
curr_deep = deep_df[deep_df['year'] == selected_year].copy() if not deep_df.empty else pd.DataFrame()

# --- 4. TOP METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Seats", len(curr_df))
col2.metric("Avg Assets", f"₹{(curr_df['assets_cleaned'].mean()/10000000):.1f} Cr")
col3.metric("Avg Criminal Cases", f"{curr_df['criminal_cases'].mean():.1f}")

if not curr_deep.empty:
    col4.metric("Avg Victory Margin", f"{int(curr_deep['margin'].mean()):,} votes")
else:
    col4.metric("Avg Victory Margin", "N/A")

st.divider()

# --- 5. VISUALIZATIONS ---
st.header("📈 Money, Crime & Trends")

c1, c2 = st.columns(2)

with c1:
    st.subheader("💰 Money vs. Crime Correlation")
    st.markdown("Do richer candidates have more criminal cases?")
    fig_scatter = px.scatter(
        curr_df, 
        x="assets_cleaned", 
        y="criminal_cases", 
        color="party",
        size="assets_cleaned",
        hover_name="candidate",
        hover_data=["constituency", "assets_cleaned"],
        log_x=True,  
        labels={"assets_cleaned": "Assets (Log Scale)", "criminal_cases": "Criminal Cases"},
        height=400
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with c2:
    st.subheader("📈 The Cost of Democracy (Trend)")
    st.markdown("Average Assets of Winners (2014-2024)")
    avg_wealth_yearly = df.groupby('year')['assets_cleaned'].mean().reset_index()
    avg_wealth_yearly['Assets (Cr)'] = avg_wealth_yearly['assets_cleaned'] / 10000000
    
    fig_line = px.line(avg_wealth_yearly, x="year", y="Assets (Cr)", markers=True, height=400)
    fig_line.update_layout(xaxis=dict(tickmode='linear', tick0=2014, dtick=5))
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# --- 6. DEEP ANALYSIS ---
if not curr_deep.empty:
    st.header(f"📊 Deep Analysis: {selected_year}")
    
    # A. REGIONAL PERFORMANCE
    st.subheader("1. Regional Breakdown")
    c1_deep, c2_deep = st.columns(2)
    
    with c1_deep:
        st.write("**Coastal vs. Rayalaseema**")
        region_summary = curr_df.groupby(['region', 'party']).size().unstack(fill_value=0)
        st.table(region_summary)
    
    with c2_deep:
        fig_region = px.bar(curr_df.groupby(['region', 'party']).size().reset_index(name='Seats'), 
                            x="region", y="Seats", color="party", barmode="group",
                            title="Seats by Region")
        st.plotly_chart(fig_region, use_container_width=True)

    st.divider()

    # B. SEAT SAFETY LEVELS
    st.subheader("2. Victory Safety Levels")
    
    c1_safe, c2_safe = st.columns(2)
    with c1_safe:
        st.write("**Safety Matrix**")
        safety_table = pd.crosstab(curr_deep['winner_party'], curr_deep['safety_level'])
        st.table(safety_table)
    
    with c2_safe:
        fig_safe = px.histogram(curr_deep, x="margin", color="winner_party", nbins=20, title="Margin Distribution")
        st.plotly_chart(fig_safe, use_container_width=True)

    # C. CLOSEST & HIGHEST WINS
    st.divider()
    c1_wins, c2_wins = st.columns(2)
    with c1_wins:
        st.markdown("##### 🥶 Nail Biters (< 2,000 Votes)")
        close_calls = curr_deep[curr_deep['margin'] < 2000].sort_values('margin')
        st.dataframe(close_calls[['constituency', 'winner', 'winner_party', 'margin']], hide_index=True)

    with c2_wins:
        st.markdown("##### 🚀 Landslides (> 50,000 Votes)")
        landslides = curr_deep[curr_deep['margin'] > 50000].sort_values('margin', ascending=False)
        st.dataframe(landslides[['constituency', 'winner', 'winner_party', 'margin']], hide_index=True)

st.divider()

# --- 7. SWING ANALYSIS ---
if selected_year == 2024:
    st.subheader("🔄 The Swing: 2019 vs 2024")
    
    df_19 = df[df['year'] == 2019][['constituency', 'party']].rename(columns={'party': 'Party_2019'})
    df_24 = df[df['year'] == 2024][['constituency', 'party']].rename(columns={'party': 'Party_2024'})
    
    swing_merge = pd.merge(df_24, df_19, on='constituency', how='inner')
    flips = swing_merge[swing_merge['Party_2019'] != swing_merge['Party_2024']]
    
    col_a, col_b = st.columns(2)
    col_a.metric("Total Seats Flipped", len(flips))
    col_a.metric("Retention Rate", f"{100 - (len(flips)/175*100):.1f}%")
    
    st.write("### 🔀 Vote Flow Matrix (Who took whose seats?)")
    st.markdown("*Rows = 2019 Winner | Columns = 2024 Winner*")
    
    flow_matrix = pd.crosstab(swing_merge['Party_2019'], swing_merge['Party_2024'])
    st.dataframe(flow_matrix) 

st.divider()

# --- 8. DETAILED SEARCH ---
st.subheader(f"🔎 Deep Constituency Search ({selected_year})")
search_term = st.text_input("Search for a Constituency (e.g., KUPPAM)", "")

if search_term and not curr_deep.empty:
    results = curr_deep[curr_deep['constituency'].str.contains(search_term.upper())]
    
    if len(results) > 0:
        for _, row in results.iterrows():
            st.markdown(f"### {row['constituency'].title()} ({row['year']})")
            
            # Show top 3 candidates
            c1_cand, c2_cand, c3_cand = st.columns(3)
            
            with c1_cand:
                st.success("🥇 Winner")
                st.markdown(f"**{row['winner']}** ({row['winner_party']})")
                st.markdown(f"**Votes:** {row['winner_votes']:,} ({row['winner_percent']}%)")
                
            with c2_cand:
                st.info("🥈 Runner Up")
                st.markdown(f"**{row['runner_up']}**")
                st.markdown(f"**Votes:** {row['runner_up_votes']:,} ({row['runner_up_percent']}%)")
                
            with c3_cand:
                st.warning("🥉 Third Place")
                st.markdown(f"**{row['third_place']}**")
                st.markdown(f"**Votes:** {row['third_place_votes']:,} ({row['third_place_percent']}%)")
                
            # Render a stacked bar chart for this constituency's vote share
            vote_data = pd.DataFrame({
                "Candidate": ["Winner", "Runner Up", "Third Place", "Others"],
                "Party": [row['winner_party'], row['runner_up_party'], row['third_place_party'], 'Other'],
                "Votes": [
                    row['winner_votes'], 
                    row['runner_up_votes'], 
                    row['third_place_votes'], 
                    row['total_votes'] - (row['winner_votes'] + row['runner_up_votes'] + row['third_place_votes'])
                ]
            })
            
            fig_bar = px.bar(
                vote_data, 
                x="Votes", 
                y=["Vote Share"]*4, 
                color="Candidate", 
                orientation='h',
                title=f"Vote Share Distribution in {row['constituency']}",
                hover_data=["Party", "Votes"],
                height=250
            )
            fig_bar.update_layout(barmode='stack', yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)
            st.divider()
    else:
        st.write("No matching constituency found.")
elif search_term and curr_deep.empty:
    st.write("Deep margin data is not available.")
else:
    # If no search term, just show the raw table
    st.write("Enter a constituency name above to see detailed candidate breakdowns.")
    if not curr_deep.empty:
        display_df = pd.merge(curr_df, curr_deep[['constituency', 'margin', 'safety_level']], on='constituency', how='left')
    else:
        display_df = curr_df
    st.dataframe(display_df, use_container_width=True, hide_index=True)
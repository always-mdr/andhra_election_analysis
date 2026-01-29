import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# --- CONFIGURATION ---
DB_STR = "postgresql://admin:password@localhost:5432/election_db"

st.set_page_config(page_title="AP Election Analytics", layout="wide")
st.title("🗳️ AP Assembly: The Complete Analysis (2014-2024)")

# --- 0. REGION MAPPING LOGIC ---
def get_region(constituency_name):
    # Rayalaseema Districts (Old)
    raya_keywords = ['KADAPA', 'KURNOOL', 'ANANTAPUR', 'CHITTOOR', 'TIRUPATI', 'HINDUPUR', 'NANDYAL', 'RAJAMPET', 'ADONI']
    if any(k in constituency_name for k in raya_keywords):
        return 'Rayalaseema'
    return 'Coastal Andhra' # Default

# --- 1. DATA LOADING ---
@st.cache_data
def load_data():
    engine = create_engine(DB_STR)
    
    # Load Main Data
    df = pd.read_sql("SELECT * FROM election_winners", engine)
    
    # Load Deep Data (Margins)
    try:
        deep_df = pd.read_sql("SELECT * FROM election_deep_metrics", engine)
    except:
        deep_df = pd.DataFrame()

    # Standardize Names
    df['constituency'] = df['constituency'].str.upper().str.strip()
    if not deep_df.empty:
        deep_df['constituency'] = deep_df['constituency'].str.upper().str.strip()

    # Standardize Parties
    df['party'] = df['party'].str.upper().str.strip()
    df['party'] = df['party'].replace({
        'YSR CONGRESS PARTY': 'YSRCP', 
        'YUVAJANA SRAMIKA RYTHU CONGRESS PARTY': 'YSRCP', 
        'TELUGU DESAM': 'TDP',
        'JANA SENA PARTY': 'JSP',
        'BHARATIYA JANATA PARTY': 'BJP'
    })
    
    # Add Region Column
    df['Region'] = df['constituency'].apply(get_region)

    return df, deep_df

try:
    df, deep_df = load_data()
except Exception as e:
    st.error(f"Database Error: {e}")
    st.stop()

# --- 2. SIDEBAR YEAR SELECTOR ---
selected_year = st.sidebar.selectbox("Select Election Year", [2024, 2019, 2014])

# --- 3. FILTER & MERGE ---
curr_df = df[df['year'] == selected_year].copy()
curr_deep = deep_df[deep_df['year'] == selected_year].copy() if not deep_df.empty else pd.DataFrame()

# Merge Party Info into Margin Data
if not curr_deep.empty and not curr_df.empty:
    curr_deep = pd.merge(curr_deep, curr_df[['constituency', 'party', 'Region']], on='constituency', how='inner')
    curr_deep.rename(columns={'party': 'winner_party'}, inplace=True)

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

# --- 5. VISUALIZATIONS (RESTORED FEATURES) ---
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
    # Group by year for the line chart
    avg_wealth_yearly = df.groupby('year')['assets_cleaned'].mean().reset_index()
    avg_wealth_yearly['Assets (Cr)'] = avg_wealth_yearly['assets_cleaned'] / 10000000
    
    fig_line = px.line(avg_wealth_yearly, x="year", y="Assets (Cr)", markers=True, height=400)
    fig_line.update_layout(xaxis=dict(tickmode='linear', tick0=2014, dtick=5))
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# --- 6. DEEP ANALYSIS (WIKIPEDIA STYLE) ---
if not curr_deep.empty:
    st.header(f"📊 Deep Analysis: {selected_year}")
    
    # A. REGIONAL PERFORMANCE
    st.subheader("1. Regional Breakdown")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Coastal vs. Rayalaseema**")
        region_summary = curr_df.groupby(['Region', 'party']).size().unstack(fill_value=0)
        st.table(region_summary)
    
    with c2:
        fig_region = px.bar(curr_df.groupby(['Region', 'party']).size().reset_index(name='Seats'), 
                            x="Region", y="Seats", color="party", barmode="group",
                            title="Seats by Region")
        st.plotly_chart(fig_region, use_container_width=True)

    st.divider()

    # B. SEAT SAFETY LEVELS
    st.subheader("2. Victory Safety Levels")
    def classify_margin(m):
        if m < 5000: return "1. Marginal (< 5k)"
        if m < 20000: return "2. Competitive (5k-20k)"
        if m < 50000: return "3. Safe (20k-50k)"
        return "4. Landslide (> 50k)"

    curr_deep['Safety'] = curr_deep['margin'].apply(classify_margin)
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Safety Matrix**")
        safety_table = pd.crosstab(curr_deep['winner_party'], curr_deep['Safety'])
        st.table(safety_table)
    
    with c2:
        fig_safe = px.histogram(curr_deep, x="margin", color="winner_party", nbins=20, title="Margin Distribution")
        st.plotly_chart(fig_safe, use_container_width=True)

    # C. CLOSEST & HIGHEST WINS
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🥶 Nail Biters (< 2,000 Votes)")
        close_calls = curr_deep[curr_deep['margin'] < 2000].sort_values('margin')
        st.dataframe(close_calls[['constituency', 'winner', 'winner_party', 'margin']], hide_index=True)

    with c2:
        st.markdown("##### 🚀 Landslides (> 50,000 Votes)")
        landslides = curr_deep[curr_deep['margin'] > 50000].sort_values('margin', ascending=False)
        st.dataframe(landslides[['constituency', 'winner', 'winner_party', 'margin']], hide_index=True)

st.divider()

# --- 7. SWING ANALYSIS (2019 vs 2024) ---
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
st.subheader(f"🔎 Constituency Search ({selected_year})")
search_term = st.text_input("Search (e.g., Kuppam)", "")

if not curr_deep.empty:
    display_df = pd.merge(curr_df, curr_deep[['constituency', 'margin', 'Safety']], on='constituency', how='left')
else:
    display_df = curr_df

if search_term:
    display_df = display_df[display_df['constituency'].str.contains(search_term.upper())]

st.dataframe(display_df, use_container_width=True, hide_index=True)
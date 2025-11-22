import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- Configuration ---
st.set_page_config(page_title="Spartans Player Development", layout="wide")

# --- Helper Functions ---
@st.cache_data
def load_data():
    # Map filenames to readable Season names
    files = {
        "NM Spartans 11U Fall 2024": "NM Spartans 11U Fall 2024 Stats.csv",
        "NM Spartans 11U Spring 2025": "NM Spartans 11U Spring 2025 Stats.csv",
        "NM Spartans 12U Fall 2025": "NM Spartans 12U Fall 2025 Stats.csv"
    }
    
    combined_data = []
    
    for season_name, filename in files.items():
        if os.path.exists(filename):
            # GameChanger CSVs usually have the category headers in row 0 and actual column names in row 1
            try:
                df = pd.read_csv(filename, header=1)
                
                # Basic cleaning
                df['Season'] = season_name
                
                # Ensure numeric conversion for stats, coercing errors to 0
                cols_to_numeric = ['AVG', 'OBP', 'SLG', 'OPS', 'PA', 'AB', 'H', 'BB', 'SO', 'QAB%', 
                                   'ERA', 'WHIP', 'IP', 'FPCT', 'BA/RISP', 'BB/K', 'SB']
                
                for col in df.columns:
                    if col in cols_to_numeric or col not in ['Number', 'Last', 'First', 'Season']:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # Create a Full Name column
                df['Full Name'] = df['First'] + " " + df['Last']
                
                # Filter out empty rows or footer info
                df = df[df['First'].notna()]
                
                combined_data.append(df)
            except Exception as e:
                st.error(f"Error loading {filename}: {e}")
    
    if combined_data:
        return pd.concat(combined_data, ignore_index=True)
    else:
        return pd.DataFrame()

def get_development_feedback(row):
    feedback = []
    
    # --- Batting Feedback ---
    if row['PA'] > 10:  # Only generate if enough plate appearances
        # Contact Logic
        if row['SO'] / row['PA'] > 0.25:
            feedback.append(("⚠️ High Strikeout Rate", 
                             f"Strikeout rate is {row['SO']/row['PA']:.1%}. Focus on two-strike approach and shortening the swing."))
        
        # Plate Discipline
        if row['QAB%'] < 40:
            feedback.append(("⚠️ Quality At-Bats", 
                             f"QAB% is {row['QAB%']}%. Needs to extend at-bats, foul off tough pitches, and draw more walks."))
        
        # Power vs Contact
        if row['SLG'] < row['OBP'] and row['AVG'] > .250:
             feedback.append(("ℹ️ Power Potential", 
                              "Good on-base skills, but Slugging is lower than OBP. Look to drive the ball into gaps rather than just making contact."))

        # Clutch
        if 'BA/RISP' in row and row['BA/RISP'] < (row['AVG'] - 0.050):
            feedback.append(("🧠 Mental Game", 
                             f"Batting Average drops with Runners in Scoring Position ({row['BA/RISP']:.3f} vs {row['AVG']:.3f}). Work on mental approach in high-pressure spots."))

    # --- Pitching Feedback ---
    if row['IP'] > 5:
        if row['BB'] > row['IP']: # More than 1 walk per inning
            feedback.append(("🎯 Pitching Control", 
                             f"Walking {row['BB']/row['IP']:.1f} batters per inning. Bullpen sessions should focus strictly on fastball command."))
        if row['WHIP'] > 1.8:
            feedback.append(("🛡️ Run Prevention", 
                             "WHIP is high. Focus on getting the first batter of the inning out to reduce traffic on base."))

    if not feedback:
        feedback.append(("✅ On Track", "Stats look solid across the board. Keep maintaining current training routine."))
        
    return feedback

# --- Main Layout ---
st.title("⚾ NM Spartans Development Dashboard")

df = load_data()

if df.empty:
    st.warning("No data found. Please ensure the CSV files are in the same directory as this script.")
else:
    # Determine the most recent season dynamically
    latest_season = "NM Spartans 12U Fall 2025"
    
    # --- View Selection ---
    view_mode = st.sidebar.radio("Select View", ["Team Summary", "Player Analysis"])

# ==========================================
    # VIEW 1: TEAM SUMMARY
    # ==========================================
    if view_mode == "Team Summary":
        st.header(f"Team Overview: {latest_season}")
        
        # Get Data for latest season
        season_df = df[df['Season'] == latest_season].copy()
        
        if season_df.empty:
            st.error(f"No data found for {latest_season}")
        else:
            # --- 1. Summary Stats Table ---
            st.subheader("📊 Team Statistics")
            
            # Select key columns for a clean summary view
            key_cols = ['Full Name', 'GP', 'PA', 'AVG', 'OPS', 'QAB%', 'H', 'RBI', 'SO', 'ERA', 'IP']
            # Only include columns that actually exist in the dataframe
            display_cols = [c for c in key_cols if c in season_df.columns]
            
            # Display table sorted by OPS by default
            st.dataframe(
                season_df[display_cols].sort_values(by='OPS', ascending=False).set_index('Full Name'),
                use_container_width=True,
                height=400
            )
            
            # --- 2. Radar Charts Grid ---
            st.divider()
            st.subheader("🕸️ Player Skill Profiles (Radar View)")
            st.markdown("Comparison of player archetypes relative to the team's best performance in each category.")
            
            metrics = {
                'Contact': 'AVG',
                'Power': 'SLG',
                'Discipline': 'OBP',
                'Speed': 'SB',
                'Fielding': 'FPCT'
            }
            
            # Calculate max values for this season once to normalize charts
            max_vals = {col: season_df[col].max() for col in metrics.values()}
            
            # Create a grid layout (3 columns wide)
            players = sorted(season_df['Full Name'].unique())
            cols = st.columns(3)
            
            for i, player in enumerate(players):
                # Get player data
                p_data = season_df[season_df['Full Name'] == player].iloc[0]
                
                # Build Radar Data
                r_values = []
                r_theta = []
                
                for label, col in metrics.items():
                    val = p_data[col]
                    m_val = max_vals[col]
                    # Normalize (0 to 1 scale)
                    norm = (val / m_val) if m_val > 0 else 0
                    r_values.append(norm)
                    r_theta.append(label)
                
                # Close the loop
                r_values.append(r_values[0])
                r_theta.append(r_theta[0])
                
                # Create Figure
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=r_values,
                    theta=r_theta,
                    fill='toself',
                    name=player,
                    line_color='royalblue'
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=False, range=[0, 1])),
                    showlegend=False,
                    title=dict(text=player, x=0.5, xanchor='center'),
                    margin=dict(t=30, b=30, l=30, r=30),
                    height=250
                )
                
                # Display in grid column
                with cols[i % 3]:
                    st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # VIEW 2: INDIVIDUAL PLAYER ANALYSIS
    # ==========================================
    elif view_mode == "Player Analysis":
        st.sidebar.header("Player Selection")
        
        # Filter to get only players present in the latest season
        if latest_season in df['Season'].unique():
            current_roster = df[df['Season'] == latest_season]['Full Name'].unique()
            player_list = sorted(current_roster)
        else:
            player_list = sorted(df['Full Name'].unique())

        selected_player = st.sidebar.selectbox("Choose a Player", player_list)
        
        # Filter Data
        player_stats = df[df['Full Name'] == selected_player].sort_values(by='Season')
        
        # --- Header Section ---
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader(f"{selected_player}")
            st.caption(f"Data Points: {len(player_stats)} Seasons")
        with col2:
            # Metric Cards (Most Recent Season)
            latest = player_stats.iloc[-1]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Current AVG", f"{latest['AVG']:.3f}")
            m2.metric("Current OPS", f"{latest['OPS']:.3f}")
            m3.metric("QAB%", f"{latest['QAB%']:.1f}%")
            m4.metric("ERA", f"{latest['ERA']:.2f}" if latest['IP'] > 0 else "N/A")

        st.divider()

        # --- Development Insights ---
        st.header("🚀 Development Focus: Next Level")
        
        insights_col, radar_col = st.columns([2, 1])
        
        with insights_col:
            st.info(f"Based on {latest['Season']} performance:")
            feedback_items = get_development_feedback(latest)
            for title, desc in feedback_items:
                st.markdown(f"**{title}**")
                st.write(desc)
                st.write("---")

        with radar_col:
            # Normalize stats against team max for the latest season
            season_df = df[df['Season'] == latest['Season']]
            
            metrics = {
                'Contact': 'AVG',
                'Power': 'SLG',
                'Discipline': 'OBP',
                'Speed': 'SB',
                'Fielding': 'FPCT'
            }
            
            r_values = []
            r_theta = []
            
            for label, col in metrics.items():
                max_val = season_df[col].max()
                player_val = latest[col]
                norm_val = (player_val / max_val) if max_val > 0 else 0
                r_values.append(norm_val)
                r_theta.append(label)
                
            # Close the loop for radar chart
            r_values.append(r_values[0])
            r_theta.append(r_theta[0])
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=r_values,
                theta=r_theta,
                fill='toself',
                name=selected_player
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=False,
                title="Skill Profile (vs Team Max)"
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # --- Statistical Trends ---
        st.header("📈 Seasonal Progression")
        
        tab1, tab2, tab3 = st.tabs(["Batting Trends", "Pitching Trends", "Raw Data"])
        
        with tab1:
            fig_bat = px.line(player_stats, x='Season', y=['AVG', 'OBP', 'OPS', 'SLG'], 
                              markers=True, title="Hitting Metrics Over Time")
            st.plotly_chart(fig_bat, use_container_width=True)
            
            fig_disc = px.bar(player_stats, x='Season', y=['QAB%', 'SO'], 
                              barmode='group', title="Discipline: Quality At-Bats % vs Strikeouts (Count)")
            st.plotly_chart(fig_disc, use_container_width=True)

        with tab2:
            if player_stats['IP'].sum() > 0:
                fig_pitch = px.line(player_stats, x='Season', y=['ERA', 'WHIP'], 
                                    markers=True, title="ERA & WHIP Progression")
                st.plotly_chart(fig_pitch, use_container_width=True)
            else:
                st.write("No pitching stats available for this player.")

        with tab3:
            st.dataframe(player_stats)
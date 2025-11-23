import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- Configuration ---
st.set_page_config(page_title="NM Spartans", layout="wide")

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
                # GameChanger CSVs have headers in row 1. 
                # Pandas handles duplicate columns (like SB, CS) by adding .1, .2 suffix.
                # Standard GC Order: Batting -> Pitching -> Fielding
                df = pd.read_csv(filename, header=1)
                
                # Rename Duplicate Columns for Clarity
                # We need to explicitly handle Pitching vs Batting stats (e.g., BB, SO appear twice)
                rename_map = {
                    # Pitching Duplicates (usually .1)
                    'BB.1': 'BB_Pitch', 'SO.1': 'SO_Pitch', 'H.1': 'H_Pitch', 'R.1': 'R_Pitch',
                    'SB.1': 'SB_Pitch', 'CS.1': 'CS_Pitch', 'PIK.1': 'PIK_Pitch',
                    
                    # Fielding/Catching Duplicates (usually .2)
                    'SB.2': 'SB_Catch', 'CS.2': 'CS_Catch', 'PIK.2': 'PIK_Catch',
                    'INN': 'INN_Catch', 'PB': 'PB'
                }
                df.rename(columns=rename_map, inplace=True)
                
                # Basic cleaning
                df['Season'] = season_name
                
                # Ensure numeric conversion for stats
                cols_to_numeric = [
                    'AVG', 'OBP', 'SLG', 'OPS', 'PA', 'AB', 'H', '1B', '2B', '3B', 'HR', 'BB', 'SO', 'QAB%', 'K-L',
                    'ERA', 'WHIP', 'IP', 'TC', 'A', 'PO', 'FPCT', 'E', 'BA/RISP', 'SB', 
                    'INN_Catch', 'PB', 'SB_Catch', 'CS_Catch',
                    'BB_Pitch', 'SO_Pitch', 'H_Pitch', 'R_Pitch'
                ]

                for col in df.columns:
                    if col in cols_to_numeric or col not in ['Number', 'Last', 'First', 'Season', 'Full Name']:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # Create a Full Name column
                df['Full Name'] = df['First'] + " " + df['Last']

                # Strikeout Percentage (avoid division by zero)
                df['SO%'] = df.apply(lambda x: (x['SO'] / x['PA'] * 100) if x['PA'] > 0 else 0, axis=1)

                # Catcher Caught Stealing % (CS%)
                # Formula: CS / (SB_Allowed + CS)
                def calc_cs_pct(row):
                    if 'SB_Catch' in row and 'CS_Catch' in row:
                        total_attempts = row['SB_Catch'] + row['CS_Catch']
                        return (row['CS_Catch'] / total_attempts * 100) if total_attempts > 0 else 0
                    return 0
                
                df['CS%_Catch'] = df.apply(calc_cs_pct, axis=1)
                
                # Passed Balls per Inning Caught (PBIC)
                df['PBIC'] = df.apply(lambda x: (x['PB'] / x['INN_Catch']) if x['INN_Catch'] > 0 else 0, axis=1)

                # Errors per Total Chances (E%)
                df['E%'] = df.apply(lambda x: (x['E'] / (x['E'] + x.get('A', 0) + x.get('PO', 0)) * 100) if (x['E'] + x.get('A', 0) + x.get('PO', 0)) > 0 else 0, axis=1)

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
        if row['SO%'] > 25:
            feedback.append(("⚠️ High Strikeout Rate", 
                             f"Strikeout rate is {row['SO']/row['PA']:.1%}. Focus on head discipline, starting with hands back, and shortening the swing."))
        
        # Plate Discipline
        if row['QAB%'] < 40:
            feedback.append(("⚠️ Quality At-Bats", 
                             f"QAB% is {row['QAB%']}%. Regardless of whether your batting average shows it, you can improve your Quality At-Bats percentage by extending at-bats, fouling off tough pitches, and drawing more walks. Take a deep breath and lock in one pitch at a time."))
        
        # Power vs Contact
        if row['SLG'] < row['OBP'] and row['AVG'] > .250:
             feedback.append(("ℹ️ Power Potential", 
                              "Good on-base skills, but Slugging Percentage is lower than On-Base Percentage, indicating that your walks are contributing more heavily towards your On-Base Percentage. Focus on keeping hands back to create a solid swing sooner while maintaining head discipline to see the ball."))

        # Clutch
        if 'BA/RISP' in row and row['BA/RISP'] < (row['AVG'] - 0.050):
            feedback.append(("🧠 Mental Game", 
                             f"Batting Average drops with Runners in Scoring Position (RISP) ({row['BA/RISP']:.3f} vs {row['AVG']:.3f}). Work on mental approach in high-pressure spots - take a deep breath and reset your mindset. Try stepping out briefly and count backwards from five. 5-4-3-2-1, go!"))

        # Overly Cautious at the Plate
        if row['K-L'] > (row['PA'] * 0.07): # More than 7% strikeouts looking
            feedback.append(("🔍 Overly Cautious at the Plate", 
                             f"Strikeouts Looking (K-L) rate is {row['K-L']/row['PA']:.1%}. Remember your technique, but start taking a few chances! If you're already striking out looking, how much worse could strikeout swinging be?"))

    # --- Fielding Feedback ---
    if row['TC'] > 50: # Only generate if enough chances
        if row['FPCT'] < 0.850:
            feedback.append(("🛡️ Fielding Fundamentals", 
                             f"Fielding Percentage is {row['FPCT']:.3f}. Emphasize footwork, glove work, throwing accuracy, and follow-through during practice. Once you field the ball, look up and establish eye contact with your target as early as possible and well before the ball leaves your hand."))

        if row['E%'] > 5:
            feedback.append(("🚫 Error Reduction", 
                             f"Error rate is {row['E%']:.1f}%. Focus on consistent mechanics and situational awareness to reduce errors. Be sure to actively communicate with your teammates!"))

    # --- Pitching Feedback ---
    if row['IP'] > 5:
        if row['BB'] > row['IP']: # More than 1 walk per inning
            feedback.append(("🎯 Pitching Control", 
                             f"Walking {row['BB']/row['IP']:.1f} batters per inning. Bullpen sessions should focus strictly on fastball command."))
        if row['WHIP'] > 1.8:
            feedback.append(("🛡️ Run Prevention", 
                             "Walks plus Hits per Inning Pitched (WHIP) is high. Focus on one batter at a time and don't be afraid to put the ball into play. Trust your defense to make the play!"))

    # --- Catching Feedback ---
    # Check if 'INN_Catch' exists and is greater than 0
    if 'INN_Catch' in row and row['INN_Catch'] > 5:
        if row['PB'] > (row['INN_Catch'] * 0.2): # More than 1 PB every 5 innings
            feedback.append(("🧱 Catcher Blocking", 
                             f"High Passed Ball rate ({row['PB']} in {row['INN_Catch']} innings). Focus on blocking drills and softer hands receiving. Take a deep breath prior to the pitch and focus on keeping eyes open as the ball approaches to better track its trajectory and execute your block."))
        
        total_attempts = row.get('SB_Catch', 0) + row.get('CS_Catch', 0)
        if total_attempts >= 5 and row['CS%_Catch'] < 10:
             feedback.append(("💪 Catcher Throwing", 
                              f"Caught Stealing % is low ({row['CS%_Catch']:.1f}%). Work on transfer speed, footwork, and arm strength. Be sure to fully step toward the target while maintaining eye contact and execute a full follow-through motion towards the glove of your infielder."))

    if not feedback:
        feedback.append(("✅ On Track", "Stats look solid across the board. Keep maintaining current training routine."))
        
    return feedback

# --- Main Layout ---
# Header with Logo Support
logo_path = "logo.png"

# Create two columns for Logo + Title if logo exists
if os.path.exists(logo_path):
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image(logo_path, width='stretch')
    with col_title:
        st.title("⚾ NM Spartans Baseball")
else:
    st.title("⚾ NM Spartans Baseball")

# Load Data
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
        st.header(f"Team Stats Overview: {latest_season}")
        
        # Get Data for latest season
        season_df = df[df['Season'] == latest_season].copy()
        
        if season_df.empty:
            st.error(f"No data found for {latest_season}")
        else:
            # --- 1. Batting ---
            st.subheader("⚔️ Batting")
            bat_cols = ['Full Name', 'GP', 'PA', 'H', 'AVG', 'OBP', 'OPS', 'SLG', 'QAB%', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K-L', 'SO%']
            display_bat = [c for c in bat_cols if c in season_df.columns]
            
            st.dataframe(
                season_df[display_bat].sort_values(by='OPS', ascending=False).set_index('Full Name').style.format({"GP": "{:.0f}", "PA": "{:.0f}", "H": "{:.0f}", "AVG": "{:.3f}", "OBP": "{:.3f}", "OPS": "{:.3f}", "SLG": "{:.3f}", "QAB%": "{:.1f}%", "1B": "{:.0f}", "2B": "{:.0f}", "3B": "{:.0f}", "HR": "{:.0f}", "RBI": "{:.0f}", "BB": "{:.0f}", "K-L": "{:.0f}", "SO%": "{:.1f}%"}),
                width='stretch', height=500
            )

            st.info("GP=Games played,  PA=Plate Appearances,  H=Hits,  AVG=Batting Average,  OBP=On-base Percentage,  OPS=On-base Plus Slugging,  SLG=Slugging Percentage,  QAB%=Quality At-Bats %,  1B=Singles, 2B=Doubles, 3B=Triples, HR=Home Runs, RBI=Runs Batted In, BB=Walks, K-L=Strikeouts Looking, SO%=Strikeout %")
            # --- 3. Fielding ---
            st.divider()
            st.subheader("🛡️ Fielding")
            field_cols = ['Full Name', 'TC', 'A', 'PO', 'FPCT', 'E', 'E%']
            display_field = [c for c in field_cols if c in season_df.columns]

            st.dataframe(
                season_df[display_field].sort_values(by='FPCT', ascending=False).set_index('Full Name').style.format({"TC": "{:.0f}", "A": "{:.0f}", "PO": "{:.0f}", "FPCT": "{:.3f}", "E": "{:.0f}", "E%": "{:.1f}%"}),
                width='stretch', height=500
            )
            st.info("TC=Total Chances,  A=Assists,  PO=Putouts,  FPCT=Fielding Percentage,  E=Errors,  E%=Errors per Total Chances")    
            
            # --- 4. Pitching ---
            st.divider()
            st.subheader("⚾ Pitching")
            pitch_df = season_df[season_df['IP'] > 0].copy()
            
            if not pitch_df.empty:
                # Define pitch columns (using renamed columns)
                pitch_cols = ['Full Name', 'IP', 'ERA', 'WHIP', 'SO_Pitch', 'BB_Pitch', 'H_Pitch']
                display_pitch = [c for c in pitch_cols if c in pitch_df.columns]
                
                st.dataframe(
                    pitch_df[display_pitch].sort_values(by='ERA', ascending=True).set_index('Full Name').style.format({"IP": "{:.2f}", "ERA": "{:.2f}", "WHIP": "{:.2f}", "SO_Pitch": "{:.0f}", "BB_Pitch": "{:.0f}", "H_Pitch": "{:.0f}"}),
                    width='stretch'
                )

                st.info("IP=Innings Pitched,  ERA=Earned Run Average,  WHIP=Walks plus Hits per Inning Pitched,  SO_Pitch=Strikeouts Pitched,  BB_Pitch=Walks Pitched,  H_Pitch=Hits Allowed")
            else:
                st.info("No pitching stats recorded for this season.")

            # --- 5. Catching ---
            st.divider()
            st.subheader("🧱 Catching")
            if 'INN_Catch' in season_df.columns:
                catchers_df = season_df[season_df['INN_Catch'] > 0].copy()
                
                if not catchers_df.empty:
                    catch_cols = ['Full Name', 'INN_Catch', 'PB', 'PBIC', 'SB_Catch', 'CS_Catch', 'CS%_Catch', 'FPCT']
                    c_display = [c for c in catch_cols if c in catchers_df.columns]
                    
                    st.dataframe(
                        catchers_df[c_display].sort_values(by='INN_Catch', ascending=False).set_index('Full Name').style.format({"INN_Catch": "{:.1f}", "PB": "{:.0f}", "PBIC": "{:.3f}", "SB_Catch": "{:.0f}", "CS_Catch": "{:.0f}", "CS%_Catch": "{:.1f}%", "FPCT": "{:.3f}"}),
                        width='stretch'
                    )

                    st.info("INN_Catch=Innings Caught,  PB=Passed Balls Allowed,  PBIC=Passed Balls Allowed per Inning Caught,   SB_Catch=Stolen Bases Allowed,  CS_Catch=Caught Stealing,  CS%_Catch=Caught Stealing Percentage,  FPCT=Fielding Percentage")
                else:
                    st.info("No catcher stats recorded for this season.")
            
            # --- 2. Radar Charts Grid ---
            st.divider()
            st.subheader("🕸️ Player Strengths")
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
                    st.plotly_chart(fig, width='stretch')

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
        latest = player_stats.iloc[-1]

        # --- Header Section ---
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader(f"{selected_player}")
            st.caption(f"Data Points: {len(player_stats)} Seasons")
        with col2:
            # Metric Cards (Most Recent Season)
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
            st.subheader("🕸️ Skill Progression (vs Team Max)")
            
            metrics = {
                'Contact': 'AVG',
                'Power': 'SLG',
                'Discipline': 'OBP',
                'Speed': 'SB',
                'Fielding': 'FPCT'
            }
            
            fig_radar = go.Figure()
            
            # Get all unique seasons for the player, sorted chronologically
            player_seasons = player_stats['Season'].unique()
            
            for i, season in enumerate(player_seasons):
                # 1. Get player's stats for this specific season
                player_season_data = player_stats[player_stats['Season'] == season].iloc[0]
                
                # 2. Get all team stats for this season (for normalization)
                team_season_df = df[df['Season'] == season]
                
                r_values = []
                r_theta = []
                
                # Calculate normalized metric values
                for label, col in metrics.items():
                    # Calculate team max for the metric in this specific season
                    max_val = team_season_df[col].max()
                    player_val = player_season_data[col]
                    
                    # Normalize against the team max (0 to 1 range)
                    norm_val = (player_val / max_val) if max_val > 0 else 0
                    
                    r_values.append(norm_val)
                    r_theta.append(label)
                
                # Close the radar shape by repeating the first value
                r_values.append(r_values[0])
                r_theta.append(r_theta[0])
                
                # Define visual style based on season (latest season should be distinct)
                line_style = {}
                fill_style = 'none' # No fill by default
                trace_name = season

                if i == len(player_seasons) - 1:
                    # Latest season: Solid line, bolder color, filled
                    line_style = dict(color='rgb(30, 144, 255)', width=3) # Dodger Blue
                    fill_style = 'toself'
                    trace_name = f"{season} (Current)"
                elif i == 0:
                    # Earliest season: Dashed line, grayed out
                    line_style = dict(color='rgba(100, 100, 100, 0.7)', dash='dash')
                else:
                    # Intermediate seasons: Dotted line
                    line_style = dict(color='rgba(100, 100, 100, 0.5)', dash='dot')

                # Add trace to radar chart
                fig_radar.add_trace(go.Scatterpolar(
                    r=r_values,
                    theta=r_theta,
                    fill=fill_style,
                    name=trace_name,
                    line=line_style,
                    opacity=1.0 if i == len(player_seasons) - 1 else 0.8
                ))
            
            # Update layout for multi-trace view
            fig_radar.update_layout(
                polar=dict(
                    # Display 0 to 1 range with percentage tick marks
                    radialaxis=dict(visible=True, range=[0, 1], tickvals=[0.25, 0.5, 0.75, 1.0], ticktext=["25%", "50%", "75%", "100%"]),
                    angularaxis=dict(rotation=90, direction='counterclockwise')
                ),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                title=dict(text=f"Skill Profile Progression", x=0.5, xanchor='center')
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # --- Statistical Trends ---
        st.header("📈 Seasonal Progression")
        
        # Check if player has catching stats to determine tabs
        has_catching = player_stats['INN_Catch'].sum() > 0
        tabs = ["Batting Trends", "Pitching Trends"]
        if has_catching:
            tabs.append("Catching Trends")
        tabs.append("Raw Data")
        
        tab_objs = st.tabs(tabs)

        # Tab 1: Batting
        with tab_objs[0]:
            fig_bat = px.line(player_stats, x='Season', y=['AVG', 'OBP', 'OPS', 'SLG'], 
                              markers=True, title="Hitting Metrics Over Time")
            fig_bat.update_yaxes(title_text="Percentage (%)")
            st.plotly_chart(fig_bat, width='stretch')
            
            fig_disc = px.bar(player_stats, x='Season', y=['QAB%', 'SO%'], 
                              barmode='group', title="Discipline: Quality At-Bats % vs Strikeout %")
            fig_disc.update_yaxes(title_text="Percentage (%)")
            st.plotly_chart(fig_disc, width='stretch')
            st.info("AVG=Batting Average,  OBP=On-base Percentage,  OPS=On-base Plus Slugging,  SLG=Slugging Percentage,  AB%=Quality At-Bats,  SO%=Strikeout %")

        # Tab 2: Fielding
        with tab_objs[1]:
            if player_stats['IP'].sum() > 0:
                fig_field = px.line(player_stats, x='Season', y=['TC', 'A', 'PO', 'FPCT', 'E', 'E%'], 
                                    markers=True, title="Fielding Percentage & Error % Progression")
                st.plotly_chart(fig_field, width='stretch')
                st.info("TC=Total Chances,  A=Assists,  PO=Putouts,  FPCT=Fielding Percentage,  E=Errors,  E%=Errors per Total Chances")
            else:
                st.write("No fielding stats available for this player.")

        # Tab 3: Pitching
        with tab_objs[2]:
            if player_stats['IP'].sum() > 0:
                fig_pitch = px.line(player_stats, x='Season', y=['ERA', 'WHIP'], 
                                    markers=True, title="ERA & WHIP Progression")
                st.plotly_chart(fig_pitch, width='stretch')
                st.info("ERA=Earned Run Average,  WHIP=Walks plus Hits per Inning Pitched,  IP=Innings Pitched")
            else:
                st.write("No pitching stats available for this player.")

        # Tab 4: Catching
        if has_catching:
            with tab_objs[3]:
                st.subheader("🛡️ Behind the Dish")
                c1, c2, c3 = st.columns(3)
                total_inn = player_stats['INN_Catch'].sum()
                total_pb = player_stats['PB'].sum()
                
                # Calculate aggregates
                total_sb_allowed = player_stats['SB_Catch'].sum()
                total_cs = player_stats['CS_Catch'].sum()
                total_att = total_sb_allowed + total_cs
                career_cs_pct = (total_cs / total_att * 100) if total_att > 0 else 0
                
                c1.metric("Innings Caught", f"{total_inn}")
                c2.metric("Total Passed Balls", f"{total_pb}")
                c3.metric("Caught Stealing %", f"{career_cs_pct:.1f}%")
                
                fig_catch = px.bar(player_stats, x='Season', y=['PB', 'SB_Catch', 'CS_Catch'],
                                   barmode='group', title="Defensive Breakdown (Count)")
                st.plotly_chart(fig_catch, width='stretch')
                st.info("PB=Passed Balls Allowed,  SB_Catch=Stolen Bases Allowed,  CS_Catch=Caught Stealing")
        
        # Raw Data Tab
        with tab_objs[-1]:
            st.dataframe(player_stats)
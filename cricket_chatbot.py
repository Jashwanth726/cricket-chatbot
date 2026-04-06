import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
import os
from io import StringIO
import base64

# Page config
st.set_page_config(
    page_title="🏏 Cricket Analysis ChatBot",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1f77b4; text-align: center; margin-bottom: 2rem;}
    .chat-message {padding: 1rem; margin: 1rem 0; border-radius: 10px; border-left: 4px solid #1f77b4;}
    .user-message {background-color: #e3f2fd; border-left-color: #2196f3;}
    .bot-message {background-color: #f5f5f5; border-left-color: #4caf50;}
    .metric-card {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def create_sample_data():
    """Create sample IPL data"""
    # Matches data
    matches_data = {
        'id': list(range(1, 101)),
        'season': [2023]*50 + [2022]*30 + [2021]*20,
        'team1': ['CSK', 'MI', 'RCB', 'KKR', 'PBKS', 'RR', 'DC', 'SRH', 'GT', 'LSG']*10,
        'team2': ['MI', 'CSK', 'GT', 'SRH', 'RR', 'PBKS', 'LSG', 'KKR', 'RCB', 'DC']*10,
        'winner': ['CSK', 'MI', 'GT', 'KKR', 'PBKS', 'RR', 'DC', 'SRH', 'CSK', 'MI']*10,
        'venue': ['MA Chidambaram', 'Wankhede', 'M Chinnaswamy', 'Eden Gardens', 'PCA Stadium', 
                 'Sawai Mansingh', 'Arun Jaitley', 'Rajiv Gandhi', 'Narendra Modi', 'Ekana']*10
    }
    
    # Deliveries data
    players = ['Virat Kohli', 'Rohit Sharma', 'MS Dhoni', 'KL Rahul', 'Shubman Gill', 
              'Jos Buttler', 'Quinton de Kock', 'David Warner', 'Rishabh Pant', 'Hardik Pandya']
    
    deliveries_data = []
    for i in range(1, 101):
        for _ in range(20):  # 20 deliveries per match
            deliveries_data.append({
                'match_id': i,
                'batsman': np.random.choice(players),
                'batsman_runs': np.random.choice([0, 1, 2, 3, 4, 6], p=[0.4, 0.2, 0.1, 0.1, 0.15, 0.05]),
                'bowler': np.random.choice(['Jasprit Bumrah', 'Rashid Khan', 'Deepak Chahar', 'Yuzvendra Chahal', 'Arshdeep Singh'])
            })
    
    return pd.DataFrame(matches_data), pd.DataFrame(deliveries_data)

class CricketChatBot:
    def __init__(self):
        self.matches_df, self.deliveries_df = create_sample_data()
        
    def preprocess_query(self, query: str) -> str:
        return re.sub(r'[^\w\s]', ' ', query.lower().strip())
    
    def detect_intent(self, query: str) -> str:
        query = self.preprocess_query(query)
        patterns = {
            'match_summary': [r'(\d{4})', r'match(?:es)?\s*(in|at)\s*(\w+)'],
            'player_stats': [r'(virat|rohit|dhoni|kl rahul|shubman|buttler|warner|pant|hardik)\s*(stats?|runs?)'],
            'team_stats': [r'(csk|mi|rcb|kkr|pbks|rr|dc|srh|gt|lsg)\s*(stats?|performance)'],
            'top_players': [r'top\s*(run|wicket)', r'best\s*(batsman|bowler)', r'most\s*(runs|wickets)'],
            'head_to_head': [r'(csk|mi|rcb)\s+(vs?|v)\s+(mi|csk|rcb)', r'head to head']
        }
        
        for intent, pats in patterns.items():
            for pat in pats:
                if re.search(pat, query, re.IGNORECASE):
                    return intent
        return 'general'
    
    def create_player_stats_plot(self, player_stats, player):
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=player_stats['match_id'],
            y=player_stats['total_runs'],
            name='Runs',
            marker_color='skyblue',
            text=player_stats['total_runs'],
            textposition='auto'
        ))
        fig.update_layout(
            title=f'🏏 {player} - Runs by Match',
            xaxis_title='Match ID',
            yaxis_title='Runs Scored',
            height=400,
            showlegend=False
        )
        return fig
    
    def create_team_wins_plot(self, team_stats):
        fig = px.bar(
            x=team_stats.index,
            y=team_stats.values,
            title="🏆 Team Wins by Season",
            color=team_stats.index,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        return fig
    
    def get_player_stats(self, player_name):
        player_data = self.deliveries_df[
            self.deliveries_df['batsman'].str.contains(player_name, case=False, na=False)
        ]
        if player_data.empty:
            return None
        
        stats = player_data.groupby(['match_id', 'batsman']).agg({
            'batsman_runs': 'sum'
        }).reset_index()
        stats.columns = ['match_id', 'player', 'total_runs']
        
        total_runs = player_data['batsman_runs'].sum()
        avg_runs = player_data['batsman_runs'].mean()
        matches = player_data['match_id'].nunique()
        
        return stats, {
            'total_runs': total_runs,
            'avg_runs': round(avg_runs, 1),
            'matches': matches
        }
    
    def get_team_stats(self, team_name):
        team_wins = self.matches_df[
            self.matches_df['winner'].str.contains(team_name, case=False)
        ]['season'].value_counts()
        return team_wins
    
    def get_response(self, query: str):
        intent = self.detect_intent(query)
        
        if intent == 'player_stats':
            player_match = re.search(r'(virat|rohit|dhoni|kl rahul|shubman|buttler|warner|pant|hardik)', 
                                   query, re.IGNORECASE)
            player = player_match.group(1).title() if player_match else "Virat Kohli"
            full_name = {'Virat': 'Virat Kohli', 'Rohit': 'Rohit Sharma', 'Dhoni': 'MS Dhoni', 
                        'Kl rahul': 'KL Rahul', 'Shubman': 'Shubman Gill'}.get(player, player)
            
            result = self.get_player_stats(full_name)
            if result:
                stats_df, summary = result
                fig = self.create_player_stats_plot(stats_df, full_name)
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🏏 Total Runs", f"{summary['total_runs']:,}")
                with col2:
                    st.metric("📊 Average", summary['avg_runs'])
                with col3:
                    st.metric("⚽ Matches", summary['matches'])
                return f"📊 Detailed stats for **{full_name}** shown above!"
            return f"❌ No data found for {full_name}. Try: Virat Kohli, Rohit Sharma, MS Dhoni"
        
        elif intent == 'team_stats':
            team_match = re.search(r'(csk|mi|rcb|kkr|pbks|rr|dc|srh|gt|lsg)', query, re.IGNORECASE)
            team = team_match.group(1).upper() if team_match else "CSK"
            
            team_wins = self.get_team_stats(team)
            if not team_wins.empty:
                fig = self.create_team_wins_plot(team_wins)
                st.plotly_chart(fig, use_container_width=True)
                st.success(f"🏆 **{team}** has won {team_wins.sum()} matches!")
                return f"📈 **{team}** performance chart above!"
            return f"❌ No data for team {team}"
        
        elif intent == 'top_players':
            top_batsmen = self.deliveries_df.groupby('batsman')['batsman_runs'].sum().nlargest(5)
            fig = px.bar(x=top_batsmen.index, y=top_batsmen.values, 
                        title="🏏 Top 5 Run Scorers", color=top_batsmen.index)
            st.plotly_chart(fig, use_container_width=True)
            return "🏆 Top run scorers shown above!"
        
        elif intent == 'match_summary':
            year_match = re.search(r'(\d{4})', query)
            year = int(year_match.group(1)) if year_match else 2023
            season_data = self.matches_df[self.matches_df['season'] == year]
            
            if not season_data.empty:
                wins = season_data['winner'].value_counts().head(5)
                fig = px.bar(x=wins.index, y=wins.values, title=f"🏆 IPL {year} - Top Teams",
                           color=wins.index, color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig, use_container_width=True)
                st.info(f"📊 IPL {year}: {len(season_data)} matches analyzed")
                return f"📈 IPL {year} summary above!"
            return f"❌ No data for {year}"
        
        else:
            return """🤖 **Welcome to Cricket Analysis ChatBot!**

**What can I help you with?**
- 👤 **Player Stats**: "Virat Kohli stats", "Rohit Sharma runs"
- 🏏 **Team Performance**: "CSK stats", "MI performance"  
- 📊 **Top Players**: "top run scorers", "best batsmen"
- 🏆 **Match Summary**: "2023 IPL summary"
- ⚔️ **Head-to-Head**: "CSK vs MI"

**Try asking**: "Virat Kohli stats" or "CSK performance"! 🎯"""

def main():
    st.markdown('<h1 class="main-header">🏏 Cricket Analysis ChatBot</h1>', unsafe_allow_html=True)
    
    # Sidebar stats
    with st.sidebar:
        st.header("📊 Quick Stats")
        bot = CricketChatBot()
        total_matches = len(bot.matches_df)
        total_teams = bot.matches_df['team1'].nunique()
        top_team = bot.matches_df['winner'].value_counts().index[0]
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("⚽ Total Matches", total_matches)
        with col2: st.metric("🏏 Teams", total_teams)
        with col3: st.metric("🥇 Top Team", top_team)
        
        st.divider()
        st.info("👈 Ask about players, teams, or matches!")
    
    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>🤖 CricketBot:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("💭 Ask about cricket stats, players, or teams..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Bot response
        with st.chat_message("assistant"):
            with st.spinner("🎯 Analyzing cricket data..."):
                bot = CricketChatBot()
                response = bot.get_response(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": str(response)})
    
    # Clear chat button
    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()

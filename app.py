import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from jira_client import JiraClient, JiraConfig
from scrum_metrics import display_scrum_metrics_enhanced
from pi_analytics import display_pi_analytics_dashboard
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Scaled Agile Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    if 'jira_client' not in st.session_state:
        st.session_state.jira_client = None
    if 'connected' not in st.session_state:
        st.session_state.connected = False

def authenticate_jira():
    st.sidebar.header("🔐 Jira Authentication")
    
    server_url = st.sidebar.text_input(
        "Jira Server URL",
        value=os.getenv("JIRA_SERVER_URL", ""),
        placeholder="https://your-jira-server.com"
    )
    
    api_token = st.sidebar.text_input(
        "Personal Access Token",
        value=os.getenv("JIRA_API_TOKEN", ""),
        type="password",
        placeholder="Your Jira Server PAT"
    )
    
    st.sidebar.caption("💡 For JIRA Server 9.12 with PAT authentication")
    
    if st.sidebar.button("Connect to Jira"):
        if server_url and api_token:
            try:
                config = JiraConfig(server=server_url, token=api_token)
                client = JiraClient(config)
                
                if client.test_connection():
                    st.session_state.jira_client = client
                    st.session_state.connected = True
                    st.sidebar.success("✅ Connected to Jira Server!")
                else:
                    st.sidebar.error("❌ Failed to connect to Jira Server")
            except Exception as e:
                st.sidebar.error(f"❌ Connection error: {str(e)}")
        else:
            st.sidebar.error("Please provide server URL and PAT")
    
    return st.session_state.connected

def display_pi_overview():
    st.header("📋 Program Increment Overview")
    
    if not st.session_state.jira_client:
        st.warning("Please connect to Jira first")
        return
    
    available_pis = st.session_state.jira_client.get_available_pis()
    
    if not available_pis:
        st.warning("No PI labels found in Jira")
        return
    
    selected_pi = st.selectbox("Select PI", available_pis)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("ART Level Metrics")
        features_df = st.session_state.jira_client.get_features_by_pi(selected_pi)
        
        if not features_df.empty:
            art_summary = features_df.groupby('art').agg({
                'key': 'count',
                'status': lambda x: (x.isin(['Done', 'Closed'])).sum()
            }).rename(columns={'key': 'total_features', 'status': 'completed_features'})
            
            art_summary['completion_rate'] = (art_summary['completed_features'] / art_summary['total_features']) * 100
            
            fig = px.bar(
                art_summary.reset_index(),
                x='art',
                y=['total_features', 'completed_features'],
                title=f"Feature Progress by ART - {selected_pi}",
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(art_summary)
    
    with col2:
        st.subheader("Workstream Breakdown")
        
        all_workstreams = st.session_state.jira_client.get_all_workstreams()
        selected_workstream = st.selectbox("Select Workstream (Optional)", ["All"] + all_workstreams)
        
        workstream_filter = None if selected_workstream == "All" else selected_workstream
        
        metrics = st.session_state.jira_client.get_pi_metrics(selected_pi, workstream_filter)
        
        if metrics:
            col2_1, col2_2, col2_3 = st.columns(3)
            
            with col2_1:
                st.metric(
                    "Feature Completion",
                    f"{metrics['completed_features']}/{metrics['total_features']}",
                    f"{metrics['feature_completion_rate']:.1f}%"
                )
            
            with col2_2:
                st.metric(
                    "Story Completion",
                    f"{metrics['completed_stories']}/{metrics['total_stories']}",
                    f"{metrics['story_completion_rate']:.1f}%"
                )
            
            with col2_3:
                st.metric(
                    "Story Points",
                    f"{metrics['completed_story_points']}/{metrics['total_story_points']}",
                    f"{metrics['story_points_completion_rate']:.1f}%"
                )

def display_feature_details():
    st.header("🎯 Feature Details")
    
    if not st.session_state.jira_client:
        st.warning("Please connect to Jira first")
        return
    
    available_pis = st.session_state.jira_client.get_available_pis()
    
    if not available_pis:
        st.warning("No PI labels found")
        return
    
    selected_pi = st.selectbox("Select PI", available_pis, key="feature_pi")
    
    features_df = st.session_state.jira_client.get_features_by_pi(selected_pi)
    
    if features_df.empty:
        st.info("No features found for selected PI")
        return
    
    st.subheader("Features Overview")
    st.dataframe(features_df, use_container_width=True)
    
    selected_feature = st.selectbox(
        "Select Feature for Story Details",
        features_df['key'].tolist(),
        format_func=lambda x: f"{x} - {features_df[features_df['key'] == x]['summary'].iloc[0]}"
    )
    
    if selected_feature:
        st.subheader(f"Stories for {selected_feature}")
        stories_df = st.session_state.jira_client.get_stories_for_feature(selected_feature)
        
        if not stories_df.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.dataframe(stories_df, use_container_width=True)
            
            with col2:
                workstream_summary = stories_df.groupby('workstream').agg({
                    'story_points': 'sum',
                    'key': 'count',
                    'status': lambda x: (x.isin(['Done', 'Closed'])).sum()
                }).rename(columns={'key': 'total_stories', 'status': 'completed_stories'})
                
                fig = px.pie(
                    workstream_summary.reset_index(),
                    names='workstream',
                    values='story_points',
                    title="Story Points by Workstream"
                )
                st.plotly_chart(fig, use_container_width=True)

def display_scrum_metrics():
    st.header("🏃‍♂️ Scrum Team Metrics")
    
    if not st.session_state.jira_client:
        st.warning("Please connect to Jira first")
        return
    
    workstreams = st.session_state.jira_client.get_all_workstreams()
    
    if not workstreams:
        st.warning("No workstreams found")
        return
    
    selected_workstream = st.selectbox("Select Workstream", workstreams)
    
    if selected_workstream:
        display_scrum_metrics_enhanced(st.session_state.jira_client, selected_workstream)

def main():
    init_session_state()
    
    st.title("📊 Scaled Agile Analytics Dashboard")
    st.markdown("Visualize your SAFe implementation progress with Jira data")
    
    if not authenticate_jira():
        st.info("👆 Please authenticate with Jira using the sidebar to get started")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["PI Overview", "PI Analytics", "Feature Details", "Scrum Metrics"])
    
    with tab1:
        display_pi_overview()
    
    with tab2:
        available_pis = st.session_state.jira_client.get_available_pis()
        if available_pis:
            selected_pi = st.selectbox("Select PI for Analytics", available_pis, key="analytics_pi")
            if selected_pi:
                display_pi_analytics_dashboard(st.session_state.jira_client, selected_pi)
        else:
            st.warning("No PI labels found")
    
    with tab3:
        display_feature_details()
    
    with tab4:
        display_scrum_metrics()

if __name__ == "__main__":
    main()
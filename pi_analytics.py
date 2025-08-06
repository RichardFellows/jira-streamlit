import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class PIAnalytics:
    def __init__(self, jira_client):
        self.jira_client = jira_client
    
    def get_pi_objectives_data(self, pi_label: str) -> Dict:
        features_df = self.jira_client.get_features_by_pi(pi_label)
        
        if features_df.empty:
            return {}
        
        objectives_by_art = {}
        
        for art in features_df['art'].unique():
            if pd.isna(art):
                continue
                
            art_features = features_df[features_df['art'] == art]
            
            total_story_points = 0
            completed_story_points = 0
            
            for _, feature in art_features.iterrows():
                stories_df = self.jira_client.get_stories_for_feature(feature['key'])
                total_story_points += stories_df['story_points'].sum()
                completed_story_points += stories_df[
                    stories_df['status'].isin(['Done', 'Closed'])
                ]['story_points'].sum()
            
            objectives_by_art[art] = {
                'committed_features': len(art_features),
                'delivered_features': len(art_features[art_features['status'].isin(['Done', 'Closed'])]),
                'committed_points': total_story_points,
                'delivered_points': completed_story_points,
                'feature_predictability': (len(art_features[art_features['status'].isin(['Done', 'Closed'])]) / len(art_features)) * 100 if len(art_features) > 0 else 0,
                'points_predictability': (completed_story_points / total_story_points) * 100 if total_story_points > 0 else 0
            }
        
        return objectives_by_art
    
    def create_pi_health_dashboard(self, pi_label: str) -> Dict[str, go.Figure]:
        objectives_data = self.get_pi_objectives_data(pi_label)
        
        if not objectives_data:
            return {}
        
        figures = {}
        
        # PI Predictability by ART
        arts = list(objectives_data.keys())
        feature_predictability = [objectives_data[art]['feature_predictability'] for art in arts]
        points_predictability = [objectives_data[art]['points_predictability'] for art in arts]
        
        fig_predictability = go.Figure(data=[
            go.Bar(name='Feature Predictability %', x=arts, y=feature_predictability, marker_color='lightblue'),
            go.Bar(name='Points Predictability %', x=arts, y=points_predictability, marker_color='lightgreen')
        ])
        fig_predictability.update_layout(
            barmode='group',
            title=f'PI Predictability by ART - {pi_label}',
            yaxis_title='Predictability (%)',
            xaxis_title='ART'
        )
        figures['predictability'] = fig_predictability
        
        # Commitment vs Delivery
        committed_features = [objectives_data[art]['committed_features'] for art in arts]
        delivered_features = [objectives_data[art]['delivered_features'] for art in arts]
        
        fig_commitment = go.Figure(data=[
            go.Bar(name='Committed', x=arts, y=committed_features, marker_color='orange', opacity=0.7),
            go.Bar(name='Delivered', x=arts, y=delivered_features, marker_color='green')
        ])
        fig_commitment.update_layout(
            barmode='group',
            title=f'Feature Commitment vs Delivery - {pi_label}',
            yaxis_title='Number of Features',
            xaxis_title='ART'
        )
        figures['commitment'] = fig_commitment
        
        # Overall PI Health Gauge
        overall_feature_predictability = sum(delivered_features) / sum(committed_features) * 100 if sum(committed_features) > 0 else 0
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = overall_feature_predictability,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"Overall PI Health - {pi_label} (%)"},
            delta = {'reference': 80},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        figures['health_gauge'] = fig_gauge
        
        return figures
    
    def create_pi_progress_timeline(self, pi_label: str) -> go.Figure:
        features_df = self.jira_client.get_features_by_pi(pi_label)
        
        if features_df.empty:
            return go.Figure()
        
        timeline_data = []
        
        for _, feature in features_df.iterrows():
            stories_df = self.jira_client.get_stories_for_feature(feature['key'])
            
            for _, story in stories_df.iterrows():
                timeline_data.append({
                    'feature': feature['key'],
                    'story': story['key'],
                    'workstream': story['workstream'],
                    'art': feature['art'],
                    'status': story['status'],
                    'created': pd.to_datetime(story['created']),
                    'updated': pd.to_datetime(story['updated']),
                    'story_points': story['story_points']
                })
        
        if not timeline_data:
            return go.Figure()
        
        timeline_df = pd.DataFrame(timeline_data)
        
        fig = px.scatter(
            timeline_df,
            x='updated',
            y='workstream',
            color='status',
            size='story_points',
            hover_data=['feature', 'story'],
            title=f'PI Progress Timeline - {pi_label}',
            color_discrete_map={
                'Done': 'green',
                'Closed': 'green',
                'In Progress': 'yellow',
                'To Do': 'red',
                'Ready': 'blue'
            }
        )
        
        fig.update_layout(
            xaxis_title='Last Updated',
            yaxis_title='Workstream',
            height=600
        )
        
        return fig
    
    def calculate_art_performance_scores(self, pi_label: str) -> pd.DataFrame:
        objectives_data = self.get_pi_objectives_data(pi_label)
        
        if not objectives_data:
            return pd.DataFrame()
        
        performance_data = []
        
        for art, data in objectives_data.items():
            predictability_score = (data['feature_predictability'] + data['points_predictability']) / 2
            
            # Quality score based on completion rate and consistency
            quality_score = min(100, data['points_predictability'] * 1.2)
            
            # Overall score
            overall_score = (predictability_score * 0.6 + quality_score * 0.4)
            
            performance_data.append({
                'ART': art,
                'Features Committed': data['committed_features'],
                'Features Delivered': data['delivered_features'],
                'Points Committed': data['committed_points'],
                'Points Delivered': data['delivered_points'],
                'Feature Predictability (%)': round(data['feature_predictability'], 1),
                'Points Predictability (%)': round(data['points_predictability'], 1),
                'Quality Score': round(quality_score, 1),
                'Overall Score': round(overall_score, 1)
            })
        
        return pd.DataFrame(performance_data)

def display_pi_analytics_dashboard(jira_client, pi_label: str):
    st.header(f"🎯 PI Analytics Dashboard - {pi_label}")
    
    pi_analytics = PIAnalytics(jira_client)
    
    # Main metrics row
    objectives_data = pi_analytics.get_pi_objectives_data(pi_label)
    
    if not objectives_data:
        st.warning("No data available for selected PI")
        return
    
    # Calculate totals
    total_committed_features = sum([data['committed_features'] for data in objectives_data.values()])
    total_delivered_features = sum([data['delivered_features'] for data in objectives_data.values()])
    total_committed_points = sum([data['committed_points'] for data in objectives_data.values()])
    total_delivered_points = sum([data['delivered_points'] for data in objectives_data.values()])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Features",
            f"{total_delivered_features}/{total_committed_features}",
            f"{((total_delivered_features/total_committed_features)*100):.1f}%" if total_committed_features > 0 else "0%"
        )
    
    with col2:
        st.metric(
            "Story Points",
            f"{total_delivered_points}/{total_committed_points}",
            f"{((total_delivered_points/total_committed_points)*100):.1f}%" if total_committed_points > 0 else "0%"
        )
    
    with col3:
        avg_feature_predictability = sum([data['feature_predictability'] for data in objectives_data.values()]) / len(objectives_data)
        st.metric("Avg Feature Predictability", f"{avg_feature_predictability:.1f}%")
    
    with col4:
        avg_points_predictability = sum([data['points_predictability'] for data in objectives_data.values()]) / len(objectives_data)
        st.metric("Avg Points Predictability", f"{avg_points_predictability:.1f}%")
    
    # Charts
    figures = pi_analytics.create_pi_health_dashboard(pi_label)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'predictability' in figures:
            st.plotly_chart(figures['predictability'], use_container_width=True)
    
    with col2:
        if 'commitment' in figures:
            st.plotly_chart(figures['commitment'], use_container_width=True)
    
    # Health gauge and timeline
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if 'health_gauge' in figures:
            st.plotly_chart(figures['health_gauge'], use_container_width=True)
    
    with col2:
        timeline_fig = pi_analytics.create_pi_progress_timeline(pi_label)
        if timeline_fig.data:
            st.plotly_chart(timeline_fig, use_container_width=True)
    
    # Performance scorecard
    st.subheader("📊 ART Performance Scorecard")
    performance_df = pi_analytics.calculate_art_performance_scores(pi_label)
    
    if not performance_df.empty:
        st.dataframe(
            performance_df.style.background_gradient(
                subset=['Overall Score'],
                cmap='RdYlGn',
                vmin=0,
                vmax=100
            ),
            use_container_width=True
        )
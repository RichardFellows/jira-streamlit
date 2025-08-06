import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List

def create_pi_burndown_chart(features_df: pd.DataFrame, stories_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Feature Progress', 'Story Points Progress'),
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    feature_status_counts = features_df['status'].value_counts()
    story_points_by_status = stories_df.groupby('status')['story_points'].sum()
    
    fig.add_trace(
        go.Bar(
            x=feature_status_counts.index,
            y=feature_status_counts.values,
            name="Features",
            marker_color='lightblue'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=story_points_by_status.index,
            y=story_points_by_status.values,
            name="Story Points",
            marker_color='lightgreen'
        ),
        row=2, col=1
    )
    
    fig.update_layout(height=600, title_text="PI Progress Overview")
    return fig

def create_art_comparison_chart(art_metrics: Dict) -> go.Figure:
    arts = list(art_metrics.keys())
    feature_completion = [art_metrics[art]['feature_completion_rate'] for art in arts]
    story_completion = [art_metrics[art]['story_completion_rate'] for art in arts]
    
    fig = go.Figure(data=[
        go.Bar(name='Feature Completion %', x=arts, y=feature_completion),
        go.Bar(name='Story Completion %', x=arts, y=story_completion)
    ])
    
    fig.update_layout(
        barmode='group',
        title='ART Performance Comparison',
        yaxis_title='Completion Rate (%)',
        xaxis_title='ART'
    )
    
    return fig

def create_workstream_velocity_chart(workstream_data: List[Dict]) -> go.Figure:
    df = pd.DataFrame(workstream_data)
    
    fig = px.line(
        df,
        x='sprint',
        y='velocity',
        color='workstream',
        title='Workstream Velocity Trends',
        markers=True
    )
    
    fig.update_layout(
        xaxis_title='Sprint',
        yaxis_title='Velocity (Story Points)',
        hovermode='x unified'
    )
    
    return fig

def create_feature_health_matrix(features_df: pd.DataFrame) -> go.Figure:
    features_df['days_in_progress'] = (
        pd.to_datetime('now') - pd.to_datetime(features_df['created'])
    ).dt.days
    
    fig = px.scatter(
        features_df,
        x='days_in_progress',
        y='status',
        color='art',
        size_max=60,
        title='Feature Health Matrix',
        hover_data=['key', 'summary']
    )
    
    fig.update_layout(
        xaxis_title='Days in Progress',
        yaxis_title='Status'
    )
    
    return fig

def create_predictability_gauge(committed: int, delivered: int) -> go.Figure:
    predictability = (delivered / committed * 100) if committed > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = predictability,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "PI Predictability (%)"},
        delta = {'reference': 80},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    return fig

def create_story_distribution_sunburst(stories_df: pd.DataFrame) -> go.Figure:
    fig = px.sunburst(
        stories_df,
        path=['art', 'workstream', 'status'],
        values='story_points',
        title='Story Points Distribution by ART and Workstream'
    )
    
    return fig
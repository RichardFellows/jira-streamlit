import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import streamlit as st

class ScrumMetricsCalculator:
    def __init__(self, jira_client):
        self.jira_client = jira_client
    
    def calculate_team_velocity(self, workstream: str, num_sprints: int = 5) -> List[Dict]:
        jql = f'customfield_20403 = "{workstream}" AND sprint is not EMPTY'
        issues = self.jira_client.jira.search_issues(jql, maxResults=1000)
        
        sprint_data = {}
        for issue in issues:
            sprint_field = getattr(issue.fields, 'customfield_sprint', None)
            if sprint_field:
                story_points = getattr(issue.fields, 'customfield_story_points', 0) or 0
                status = issue.fields.status.name
                
                if sprint_field not in sprint_data:
                    sprint_data[sprint_field] = {
                        'total_points': 0,
                        'completed_points': 0,
                        'total_stories': 0,
                        'completed_stories': 0
                    }
                
                sprint_data[sprint_field]['total_points'] += story_points
                sprint_data[sprint_field]['total_stories'] += 1
                
                if status in ['Done', 'Closed']:
                    sprint_data[sprint_field]['completed_points'] += story_points
                    sprint_data[sprint_field]['completed_stories'] += 1
        
        velocity_data = []
        for sprint, data in list(sprint_data.items())[-num_sprints:]:
            velocity_data.append({
                'sprint': sprint,
                'workstream': workstream,
                'velocity': data['completed_points'],
                'planned_points': data['total_points'],
                'completion_rate': (data['completed_points'] / data['total_points'] * 100) if data['total_points'] > 0 else 0
            })
        
        return velocity_data
    
    def calculate_cycle_time(self, workstream: str) -> pd.DataFrame:
        jql = f'customfield_20403 = "{workstream}" AND status = "Done"'
        issues = self.jira_client.jira.search_issues(jql, expand='changelog', maxResults=500)
        
        cycle_times = []
        for issue in issues:
            created_date = pd.to_datetime(issue.fields.created)
            
            done_date = None
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.field == 'status' and item.toString in ['Done', 'Closed']:
                        done_date = pd.to_datetime(history.created)
                        break
                if done_date:
                    break
            
            if done_date:
                cycle_time = (done_date - created_date).days
                cycle_times.append({
                    'issue_key': issue.key,
                    'created': created_date,
                    'completed': done_date,
                    'cycle_time_days': cycle_time,
                    'story_points': getattr(issue.fields, 'customfield_story_points', 0) or 0
                })
        
        return pd.DataFrame(cycle_times)
    
    def create_burndown_chart(self, workstream: str, sprint: str) -> go.Figure:
        jql = f'customfield_20403 = "{workstream}" AND sprint = "{sprint}"'
        issues = self.jira_client.jira.search_issues(jql, expand='changelog', maxResults=500)
        
        total_points = sum([getattr(issue.fields, 'customfield_story_points', 0) or 0 for issue in issues])
        
        burndown_data = []
        current_date = datetime.now() - timedelta(days=14)  # Assume 2-week sprint
        remaining_points = total_points
        
        for day in range(15):
            date = current_date + timedelta(days=day)
            
            points_completed_by_date = 0
            for issue in issues:
                for history in issue.changelog.histories:
                    history_date = pd.to_datetime(history.created).date()
                    if history_date <= date.date():
                        for item in history.items:
                            if item.field == 'status' and item.toString in ['Done', 'Closed']:
                                points_completed_by_date += getattr(issue.fields, 'customfield_story_points', 0) or 0
            
            remaining_points = total_points - points_completed_by_date
            burndown_data.append({
                'date': date,
                'remaining_points': remaining_points,
                'ideal_remaining': total_points - (total_points / 14 * day)
            })
        
        df = pd.DataFrame(burndown_data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['remaining_points'],
            mode='lines+markers',
            name='Actual',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ideal_remaining'],
            mode='lines',
            name='Ideal',
            line=dict(color='gray', dash='dash')
        ))
        
        fig.update_layout(
            title=f'Sprint Burndown - {workstream} - {sprint}',
            xaxis_title='Date',
            yaxis_title='Remaining Story Points'
        )
        
        return fig
    
    def create_velocity_chart(self, workstream: str) -> go.Figure:
        velocity_data = self.calculate_team_velocity(workstream)
        
        if not velocity_data:
            fig = go.Figure()
            fig.add_annotation(text="No velocity data available", x=0.5, y=0.5)
            return fig
        
        df = pd.DataFrame(velocity_data)
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Velocity Trend', 'Commitment vs Delivery'),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        fig.add_trace(
            go.Bar(x=df['sprint'], y=df['velocity'], name='Velocity'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['sprint'],
                y=df['velocity'].rolling(window=3).mean(),
                mode='lines',
                name='3-Sprint Average',
                line=dict(color='red')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=df['sprint'], y=df['planned_points'], name='Planned', opacity=0.7),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(x=df['sprint'], y=df['velocity'], name='Delivered'),
            row=2, col=1
        )
        
        fig.update_layout(height=600, title_text=f"Velocity Analysis - {workstream}")
        return fig
    
    def create_cycle_time_chart(self, workstream: str) -> go.Figure:
        cycle_time_df = self.calculate_cycle_time(workstream)
        
        if cycle_time_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No cycle time data available", x=0.5, y=0.5)
            return fig
        
        fig = px.scatter(
            cycle_time_df,
            x='completed',
            y='cycle_time_days',
            size='story_points',
            hover_data=['issue_key'],
            title=f'Cycle Time Analysis - {workstream}'
        )
        
        avg_cycle_time = cycle_time_df['cycle_time_days'].mean()
        fig.add_hline(
            y=avg_cycle_time,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Average: {avg_cycle_time:.1f} days"
        )
        
        fig.update_layout(
            xaxis_title='Completion Date',
            yaxis_title='Cycle Time (Days)'
        )
        
        return fig

def display_scrum_metrics_enhanced(jira_client, workstream: str):
    st.subheader(f"📈 Scrum Metrics for {workstream}")
    
    metrics_calculator = ScrumMetricsCalculator(jira_client)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            metrics_calculator.create_velocity_chart(workstream),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            metrics_calculator.create_cycle_time_chart(workstream),
            use_container_width=True
        )
    
    velocity_data = metrics_calculator.calculate_team_velocity(workstream)
    if velocity_data:
        df = pd.DataFrame(velocity_data)
        avg_velocity = df['velocity'].mean()
        last_velocity = df['velocity'].iloc[-1] if not df.empty else 0
        
        col3, col4, col5 = st.columns(3)
        with col3:
            st.metric("Average Velocity", f"{avg_velocity:.1f}", f"{last_velocity - avg_velocity:+.1f}")
        
        with col4:
            avg_completion = df['completion_rate'].mean()
            st.metric("Avg Sprint Completion", f"{avg_completion:.1f}%")
        
        with col5:
            predictability = df['completion_rate'].std()
            st.metric("Predictability (Lower Better)", f"{predictability:.1f}%")
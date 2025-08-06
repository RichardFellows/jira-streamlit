# Scaled Agile Analytics Dashboard

A Streamlit application for visualizing Jira data to track scaled agile practices, featuring PI (Program Increment) tracking, ART (Agile Release Train) metrics, and scrum team performance.

## Features

- **PI Overview**: Track committed vs delivered features by ART and workstream
- **PI Analytics**: Comprehensive dashboard with predictability metrics, health gauges, and performance scorecards
- **Feature Details**: Drill-down view of features and their associated stories
- **Scrum Metrics**: Velocity tracking, cycle time analysis, and sprint burndown charts

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Jira Server URL, PAT, and PI labels
   ```

3. **Run the Application**
   ```bash
   streamlit run app.py
   ```

## Jira Configuration Requirements

### Custom Fields
The application uses the following custom fields from your Jira instance:
- `customfield_10003`: Story points estimation
- `customfield_20403`: Scrum team name (workstream)
- `customfield_11800`: Business benefit for features
- `customfield_11701`: Sprint information
- `customfield_11702`: Link from stories to their parent feature

### Issue Types and Labels
- **Feature**: Issue type for high-level features
- **PI Labels**: Format `PI-X_ART_NAME` (e.g., `PI-3_Reporting`, `PI-4_Reporting`, `PI-5_Reporting`)
- **Configurable**: PI labels can be customized in the sidebar or via environment variables

## Usage

1. **Authentication**: Enter your JIRA Server URL and Personal Access Token in the sidebar
2. **Configure PI Labels**: Set up your PI labels (defaults to PI-3_Reporting, PI-4_Reporting, PI-5_Reporting)
3. **Connect**: Click "Connect to Jira" to establish connection
4. **Select PI**: Choose a Program Increment to analyze from your configured labels
5. **View Metrics**: Navigate between tabs to see different views:
   - PI Overview: High-level progress by ART
   - PI Analytics: Detailed performance metrics and health indicators
   - Feature Details: Individual feature and story tracking
   - Scrum Metrics: Team-level velocity and cycle time analysis

## JIRA Server Authentication

This application is configured for **JIRA Server 9.12** with:
- REST API v2
- Personal Access Token (PAT) authentication
- Bearer token authorization (no email required)

## Architecture

- `app.py`: Main Streamlit application
- `jira_client.py`: Jira API connection and data retrieval
- `models.py`: Data models for features, stories, and metrics
- `visualizations.py`: Plotly chart creation utilities
- `scrum_metrics.py`: Scrum team specific calculations and visualizations
- `pi_analytics.py`: Program Increment specific analytics and dashboards

## Security

- Personal Access Tokens are handled securely through environment variables
- No credentials are stored in the application code
- Bearer token authentication for JIRA Server
- Connection testing validates authentication before proceeding
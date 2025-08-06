# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Streamlit application for visualizing JIRA Server data to support scaled agile practices. The app tracks Program Increment (PI) commitments, ART (Agile Release Train) performance, and scrum team metrics using custom Jira fields and labels.

**Target Platform**: JIRA Server 9.12 with REST API v2 and PAT authentication

## Development Commands

1. **Environment Setup**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or: venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Run Application**
   ```bash
   streamlit run app.py
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with actual Jira credentials
   ```

## Architecture Overview

### Core Modules
- `app.py`: Main Streamlit UI with authentication and tab navigation
- `jira_client.py`: Jira API wrapper handling custom fields and PI label parsing
- `models.py`: Data classes for Features, Stories, and various metrics
- `scrum_metrics.py`: Team-level velocity, cycle time, and burndown calculations
- `pi_analytics.py`: PI-specific dashboards with predictability and health metrics
- `visualizations.py`: Reusable Plotly chart generators

### Custom Field Mapping
The application uses these Jira custom fields:
- `customfield_10003`: Story point estimates
- `customfield_20403`: Scrum team identifier (workstream)
- `customfield_11800`: Business benefit for features
- `customfield_11701`: Sprint assignment
- `customfield_11702`: Story-to-feature relationship

### PI Label Format
Features must have labels in format: `PI-X_ART_NAME` (e.g., `PI-1_Reporting`, `PI-2_Grading`)

## Key Implementation Patterns

### Authentication Flow
- User provides JIRA Server URL and PAT via sidebar
- `JiraClient` uses Bearer token authentication for Server v2 API
- Connection testing validates PAT before data retrieval
- Credentials stored in Streamlit session state (not persisted)

### Data Retrieval Strategy
- `get_features_by_pi()`: Fetches features by PI label, extracts ART from labels
- `get_stories_for_feature()`: Gets stories via feature_link custom field
- Metrics calculated on-demand for selected PI/workstream combinations

### Visualization Architecture
- Each major view (PI Overview, Analytics, Scrum Metrics) has dedicated functions
- Plotly figures created through specialized modules
- Charts support filtering by ART, workstream, and time ranges

## Security Considerations

- PAT tokens handled via environment variables and session state only
- Bearer token authentication (no email required)
- No credential persistence or logging
- JIRA Server connection tested before data retrieval
- Error handling prevents credential exposure in stack traces
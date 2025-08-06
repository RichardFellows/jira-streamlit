import os
from typing import List, Dict, Optional
from jira import JIRA
import pandas as pd
from dataclasses import dataclass
import streamlit as st
from logger_config import setup_logger, log_function_call, log_user_action

# Set up logger for this module
logger = setup_logger('jira_client')

@dataclass
class JiraConfig:
    server: str
    token: str

class JiraClient:
    def __init__(self, config: JiraConfig):
        self.config = config
        self.jira = None
        logger.info(f"Initializing JiraClient for server: {config.server}")
        self._connect()
    
    def _connect(self):
        try:
            logger.info(f"Connecting to JIRA Server: {self.config.server}")
            # For JIRA Server 9.12 with PAT authentication
            options = {
                'server': self.config.server,
                'rest_api_version': '2'
            }
            self.jira = JIRA(
                options=options,
                token_auth=self.config.token
            )
            logger.info("JIRA connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to JIRA: {str(e)}", exc_info=True)
            st.error(f"Failed to connect to Jira: {str(e)}")
            raise
    
    @log_function_call(logger, log_result=True)
    def test_connection(self) -> bool:
        try:
            user = self.jira.current_user()
            logger.info(f"Connection test successful - User: {user}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    @log_function_call(logger, log_args=True, log_result=True)
    def get_features_by_pi(self, pi_label: str) -> pd.DataFrame:
        jql = f'issueType = "Feature" AND labels = "{pi_label}"'
        logger.info(f"Executing JQL query: {jql}")
        issues = self.jira.search_issues(jql, expand='changelog', maxResults=1000)
        logger.info(f"Found {len(issues)} features for PI: {pi_label}")
        
        features_data = []
        for issue in issues:
            art = self._extract_art_from_label(issue.fields.labels)
            pi = self._extract_pi_from_label(issue.fields.labels)
            
            features_data.append({
                'key': issue.key,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'art': art,
                'pi': pi,
                'business_benefit': getattr(issue.fields, 'customfield_11800', None),
                'created': issue.fields.created,
                'updated': issue.fields.updated
            })
        
        return pd.DataFrame(features_data)
    
    @log_function_call(logger, log_args=True, log_result=True)
    def get_stories_for_feature(self, feature_key: str) -> pd.DataFrame:
        jql = f'customfield_11702 = "{feature_key}" OR "Epic Link" = "{feature_key}"'
        logger.info(f"Executing JQL query for feature stories: {jql}")
        issues = self.jira.search_issues(jql, expand='changelog', maxResults=1000)
        logger.info(f"Found {len(issues)} stories for feature: {feature_key}")
        
        stories_data = []
        for issue in issues:
            stories_data.append({
                'key': issue.key,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'story_points': getattr(issue.fields, 'customfield_10003', 0) or 0,
                'workstream': self._get_workstream_safe(issue),
                'sprint': getattr(issue.fields, 'customfield_11701', None),
                'feature_link': getattr(issue.fields, 'customfield_11702', feature_key),
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                'created': issue.fields.created,
                'updated': issue.fields.updated
            })
        
        return pd.DataFrame(stories_data)
    
    def _get_workstream_safe(self, issue) -> str:
        """Safely extract workstream, handling missing field gracefully."""
        try:
            workstream = getattr(issue.fields, 'customfield_20403', None)
            if workstream and workstream.strip():
                return workstream.strip()
            else:
                return 'Unknown'
        except Exception as e:
            logger.warning(f"Error extracting workstream from issue {issue.key}: {e}")
            return 'Unknown'
    
    @log_function_call(logger, log_result=True)
    def get_all_workstreams(self) -> List[str]:
        # First try to get issues with workstream field populated
        try:
            jql_with_workstream = 'customfield_20403 is not EMPTY'
            logger.info(f"Querying for workstreams with JQL: {jql_with_workstream}")
            issues = self.jira.search_issues(jql_with_workstream, maxResults=1000)
            logger.info(f"Found {len(issues)} issues with workstream field populated")
        except Exception as e:
            logger.warning(f"Query for workstream field failed: {e}, falling back to broader search")
            # Fallback: get all issues and extract workstreams client-side
            jql_fallback = 'project is not EMPTY'
            issues = self.jira.search_issues(jql_fallback, maxResults=1000)
            logger.info(f"Fallback query returned {len(issues)} issues")
        
        workstreams = set()
        unknown_count = 0
        
        for issue in issues:
            workstream = self._get_workstream_safe(issue)
            workstreams.add(workstream)
            if workstream == 'Unknown':
                unknown_count += 1
        
        logger.info(f"Extracted workstreams: {len(workstreams)} unique values, {unknown_count} unknown")
        
        # Sort but put 'Unknown' at the end
        sorted_workstreams = sorted([w for w in workstreams if w != 'Unknown'])
        if 'Unknown' in workstreams:
            sorted_workstreams.append('Unknown')
        
        return sorted_workstreams
    
    @log_function_call(logger, log_args=True, log_result=True)
    def get_pi_metrics(self, pi_label: str, workstream: Optional[str] = None) -> Dict:
        features_df = self.get_features_by_pi(pi_label)
        
        if features_df.empty:
            return {}
        
        total_stories = 0
        completed_stories = 0
        total_story_points = 0
        completed_story_points = 0
        
        for _, feature in features_df.iterrows():
            stories_df = self.get_stories_for_feature(feature['key'])
            
            # Log workstream field coverage
            if not stories_df.empty:
                unknown_count = len(stories_df[stories_df['workstream'] == 'Unknown'])
                if unknown_count > 0:
                    logger.info(f"Feature {feature['key']}: {unknown_count}/{len(stories_df)} stories have unknown workstream")
            
            if workstream:
                stories_df = stories_df[stories_df['workstream'] == workstream]
            
            total_stories += len(stories_df)
            completed_stories += len(stories_df[stories_df['status'].isin(['Done', 'Closed'])])
            
            total_story_points += stories_df['story_points'].sum()
            completed_story_points += stories_df[
                stories_df['status'].isin(['Done', 'Closed'])
            ]['story_points'].sum()
        
        return {
            'total_features': len(features_df),
            'completed_features': len(features_df[features_df['status'].isin(['Done', 'Closed'])]),
            'total_stories': total_stories,
            'completed_stories': completed_stories,
            'total_story_points': total_story_points,
            'completed_story_points': completed_story_points,
            'feature_completion_rate': (len(features_df[features_df['status'].isin(['Done', 'Closed'])]) / len(features_df)) * 100 if len(features_df) > 0 else 0,
            'story_completion_rate': (completed_stories / total_stories) * 100 if total_stories > 0 else 0,
            'story_points_completion_rate': (completed_story_points / total_story_points) * 100 if total_story_points > 0 else 0
        }
    
    def _extract_art_from_label(self, labels: List) -> Optional[str]:
        for label in labels:
            if label.startswith('PI-'):
                parts = label.split('_')
                if len(parts) > 1:
                    return parts[1]
        return None
    
    def _extract_pi_from_label(self, labels: List) -> Optional[str]:
        for label in labels:
            if label.startswith('PI-'):
                parts = label.split('_')
                if len(parts) > 0:
                    return parts[0]
        return None
    
    @log_function_call(logger, log_args=True, log_result=True)
    def get_available_pis(self, pi_labels: List[str] = None) -> List[str]:
        # If specific PI labels are provided, check which ones exist in JIRA
        if pi_labels:
            # Build JQL to search for specific labels
            label_conditions = ' OR '.join([f'labels = "{label}"' for label in pi_labels])
            jql = f'issueType = "Feature" AND ({label_conditions})'
            
            try:
                issues = self.jira.search_issues(jql, maxResults=1000)
                found_pis = set()
                for issue in issues:
                    if issue.fields.labels:
                        for label in issue.fields.labels:
                            if label in pi_labels:
                                found_pis.add(label)
                return sorted(list(found_pis))
            except Exception:
                # Fallback to client-side filtering if JQL fails
                pass
        
        # Fallback: Get all Features and filter client-side
        jql = 'issueType = "Feature"'
        issues = self.jira.search_issues(jql, maxResults=1000)
        
        pis = set()
        for issue in issues:
            if issue.fields.labels:
                for label in issue.fields.labels:
                    # If specific labels provided, only include those
                    if pi_labels:
                        if label in pi_labels:
                            pis.add(label)
                    else:
                        # Otherwise include any label starting with PI-
                        if label.startswith('PI-'):
                            pis.add(label)
        
        return sorted(list(pis))
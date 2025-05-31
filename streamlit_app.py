import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import django
from django.db.models import Count, Avg, Sum, F, Q
from django.utils import timezone
import datetime
import numpy as np

# Set up Django integration
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')
try:
    django.setup()
    from django.contrib.auth.models import User
    from core.models import (
        Profile, PersonalityTest, UserTestResult, Scenario, 
        UserScenarioProgress, DailyChallenge, UserActivity,
        DynamicScenario, Mentor, MentorChat, SupportIssue
    )
    django_setup_success = True
except Exception as e:
    django_setup_success = False
    django_error = str(e)

# Page configuration
st.set_page_config(
    page_title="DesiQ Analytics Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4B5EAA;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #6C757D;
        margin-bottom: 1rem;
    }
    .chart-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #495057;
        margin-bottom: 0.5rem;
    }
    .stat-box {
        background-color: #F8F9FA;
        border-radius: 5px;
        padding: 1rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4B5EAA;
    }
    .stat-label {
        font-size: 1rem;
        color: #6C757D;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>DesiQ Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Interactive visualization of user progress and platform metrics</p>", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a page",
    ["Overview", "User Analytics", "Personality Tests", "Scenarios", "Mentor Chats", "Support Issues"]
)

# Check if Django is properly configured
if not django_setup_success:
    st.error(f"⚠️ Failed to connect to Django: {django_error}")
    st.info("""
    This dashboard requires connection to the Django database. Please ensure:
    1. The Django application is properly configured
    2. You're running this from the correct directory
    3. Django settings are properly set up
    
    Try running this command in your terminal:
    ```
    python -c "import django; django.setup()"
    ```
    """)
    st.stop()

# Helper functions for data retrieval
def get_user_stats():
    total_users = User.objects.count()
    active_users = Profile.objects.filter(last_activity__gte=timezone.now() - datetime.timedelta(days=7)).count()
    premium_users = Profile.objects.filter(is_premium=True).count()
    avg_level = Profile.objects.aggregate(avg_level=Avg('level'))['avg_level']
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "premium_users": premium_users,
        "premium_percentage": (premium_users / total_users * 100) if total_users > 0 else 0,
        "avg_level": avg_level or 0
    }

def get_test_stats():
    total_tests = PersonalityTest.objects.count()
    total_results = UserTestResult.objects.count()
    popular_tests = UserTestResult.objects.values('test__title').annotate(
        count=Count('test')).order_by('-count')[:5]
    
    return {
        "total_tests": total_tests,
        "total_results": total_results,
        "popular_tests": popular_tests
    }

def get_scenario_stats():
    total_scenarios = Scenario.objects.count()
    completed_scenarios = UserScenarioProgress.objects.filter(completed=True).count()
    scenarios_by_category = Scenario.objects.values('category').annotate(count=Count('id'))
    
    return {
        "total_scenarios": total_scenarios,
        "completed_scenarios": completed_scenarios,
        "scenarios_by_category": scenarios_by_category
    }

def get_activity_data():
    # Get activity counts by type for the last 30 days
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    activity_by_type = UserActivity.objects.filter(
        created_at__gte=thirty_days_ago
    ).values('activity_type').annotate(count=Count('id')).order_by('-count')
    
    # Get activity by day for the last 30 days
    activity_by_day = UserActivity.objects.filter(
        created_at__gte=thirty_days_ago
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    return {
        "activity_by_type": activity_by_type,
        "activity_by_day": activity_by_day
    }

# Page content
if page == "Overview":
    st.markdown("## Platform Overview")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    user_stats = get_user_stats()
    test_stats = get_test_stats()
    scenario_stats = get_scenario_stats()
    
    with col1:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{user_stats['total_users']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Total Users</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{user_stats['active_users']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Active Users (7d)</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{test_stats['total_results']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Tests Taken</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{scenario_stats['completed_scenarios']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Scenarios Completed</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Premium user distribution
    st.markdown("### User Distribution")
    col1, col2 = st.columns(2)
    
    with col1:
        premium_data = [
            user_stats['premium_users'], 
            user_stats['total_users'] - user_stats['premium_users']
        ]
        premium_labels = ['Premium', 'Free']
        fig = go.Figure(data=[go.Pie(
            labels=premium_labels,
            values=premium_data,
            hole=.4,
            marker_colors=['#4B5EAA', '#F9C74F']
        )])
        fig.update_layout(title_text="Premium vs Free Users")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        try:
            # User levels distribution
            user_levels = list(Profile.objects.values_list('level', flat=True))
            level_counts = pd.Series(user_levels).value_counts().sort_index()
            
            fig = px.bar(
                x=level_counts.index.tolist(),
                y=level_counts.values.tolist(),
                labels={'x': 'User Level', 'y': 'Number of Users'},
                title="User Level Distribution"
            )
            fig.update_layout(xaxis_title="User Level", yaxis_title="Number of Users")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating level distribution chart: {e}")
    
    # Activity data
    st.markdown("### User Activity (Last 30 Days)")
    try:
        activity_data = get_activity_data()
        
        if activity_data["activity_by_day"]:
            df_activity = pd.DataFrame(list(activity_data["activity_by_day"]))
            df_activity['day'] = pd.to_datetime(df_activity['day'])
            
            fig = px.line(
                df_activity, 
                x='day', 
                y='count',
                labels={'day': 'Date', 'count': 'Activity Count'},
                title="Daily User Activity"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No activity data available for the selected period.")
    except Exception as e:
        st.error(f"Error generating activity chart: {e}")

elif page == "User Analytics":
    st.markdown("## User Analytics")
    
    # User growth over time
    st.markdown("### User Growth")
    try:
        # Get user creation dates
        users = User.objects.all().order_by('date_joined')
        user_dates = [u.date_joined.date() for u in users]
        
        if user_dates:
            # Convert to dataframe and count cumulative users by date
            df_users = pd.DataFrame({'date_joined': user_dates})
            df_users['count'] = 1
            df_users = df_users.groupby('date_joined').count().reset_index()
            df_users['cumulative'] = df_users['count'].cumsum()
            
            fig = px.line(
                df_users,
                x='date_joined',
                y='cumulative',
                labels={'date_joined': 'Date', 'cumulative': 'Total Users'},
                title="Cumulative User Growth"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No user data available.")
    except Exception as e:
        st.error(f"Error generating user growth chart: {e}")
    
    # User stats by attributes
    st.markdown("### User Attributes")
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            # Average scores
            avg_scores = Profile.objects.aggregate(
                avg_rationality=Avg('rationality_score'),
                avg_decisiveness=Avg('decisiveness_score'),
                avg_empathy=Avg('empathy_score'),
                avg_clarity=Avg('clarity_score')
            )
            
            score_labels = ['Rationality', 'Decisiveness', 'Empathy', 'Clarity']
            score_values = [
                avg_scores['avg_rationality'] or 0,
                avg_scores['avg_decisiveness'] or 0,
                avg_scores['avg_empathy'] or 0,
                avg_scores['avg_clarity'] or 0
            ]
            
            fig = px.bar(
                x=score_labels,
                y=score_values,
                labels={'x': 'Attribute', 'y': 'Average Score'},
                title="Average User Attribute Scores",
                color=score_values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating attribute scores chart: {e}")
    
    with col2:
        try:
            # MBTI distribution
            mbti_counts = Profile.objects.exclude(
                mbti_type__isnull=True
            ).exclude(
                mbti_type__exact=''
            ).values('mbti_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if mbti_counts:
                df_mbti = pd.DataFrame(list(mbti_counts))
                fig = px.pie(
                    df_mbti,
                    values='count',
                    names='mbti_type',
                    title="MBTI Type Distribution"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No MBTI data available.")
        except Exception as e:
            st.error(f"Error generating MBTI chart: {e}")

elif page == "Personality Tests":
    st.markdown("## Personality Tests Analytics")
    
    # Test completion statistics
    test_stats = get_test_stats()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{test_stats['total_tests']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Total Tests Available</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{test_stats['total_results']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Tests Completed</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Popular tests chart
    st.markdown("### Most Popular Tests")
    try:
        if test_stats['popular_tests']:
            df_popular = pd.DataFrame(list(test_stats['popular_tests']))
            fig = px.bar(
                df_popular,
                x='test__title',
                y='count',
                labels={'test__title': 'Test', 'count': 'Completions'},
                title="Most Popular Personality Tests",
                color='count',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_title="Test", yaxis_title="Number of Completions")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No test completion data available.")
    except Exception as e:
        st.error(f"Error generating popular tests chart: {e}")
    
    # Test results distribution
    st.markdown("### Test Results Distribution")
    
    try:
        # Get all tests
        tests = PersonalityTest.objects.all()
        
        if tests:
            selected_test = st.selectbox(
                "Select a test to view results distribution:",
                options=[test.title for test in tests],
                index=0
            )
            
            # Get results for the selected test
            selected_test_obj = PersonalityTest.objects.get(title=selected_test)
            test_results = UserTestResult.objects.filter(
                test=selected_test_obj
            ).values('result__title').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if test_results:
                df_results = pd.DataFrame(list(test_results))
                fig = px.pie(
                    df_results,
                    values='count',
                    names='result__title',
                    title=f"Results Distribution for {selected_test}"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No results available for {selected_test}.")
        else:
            st.info("No personality tests available in the database.")
    except Exception as e:
        st.error(f"Error generating test results chart: {e}")

elif page == "Scenarios":
    st.markdown("## Scenario Analytics")
    
    scenario_stats = get_scenario_stats()
    
    # Key metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{scenario_stats['total_scenarios']}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Total Scenarios</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        completion_rate = (scenario_stats['completed_scenarios'] / (UserScenarioProgress.objects.count() or 1)) * 100
        st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='stat-value'>{completion_rate:.1f}%</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Scenario Completion Rate</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Scenarios by category
    st.markdown("### Scenarios by Category")
    try:
        if scenario_stats['scenarios_by_category']:
            df_categories = pd.DataFrame(list(scenario_stats['scenarios_by_category']))
            fig = px.pie(
                df_categories,
                values='count',
                names='category',
                title="Scenario Distribution by Category"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No scenario category data available.")
    except Exception as e:
        st.error(f"Error generating scenario categories chart: {e}")
    
    # Daily challenges completion
    st.markdown("### Daily Challenge Completion Rate (Last 30 Days)")
    try:
        thirty_days_ago = timezone.now().date() - datetime.timedelta(days=30)
        
        daily_challenges = DailyChallenge.objects.filter(
            date_created__gte=thirty_days_ago
        ).values('date_created').annotate(
            total=Count('id'),
            completed=Sum(Case(When(completed=True, then=1), default=0, output_field=IntegerField()))
        ).order_by('date_created')
        
        if daily_challenges:
            df_challenges = pd.DataFrame(list(daily_challenges))
            df_challenges['completion_rate'] = (df_challenges['completed'] / df_challenges['total']) * 100
            
            fig = px.line(
                df_challenges,
                x='date_created',
                y='completion_rate',
                labels={'date_created': 'Date', 'completion_rate': 'Completion Rate (%)'},
                title="Daily Challenge Completion Rate"
            )
            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily challenge data available for the selected period.")
    except Exception as e:
        st.error(f"Error generating daily challenge chart: {e}")

elif page == "Mentor Chats":
    st.markdown("## Mentor Chat Analytics")
    
    # Key metrics
    try:
        total_mentors = Mentor.objects.count()
        total_chats = MentorChat.objects.count()
        avg_msgs_per_user = MentorChat.objects.values('user').annotate(
            msg_count=Count('id')
        ).aggregate(avg=Avg('msg_count'))['avg']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{total_mentors}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Available Mentors</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{total_chats}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Total Chat Messages</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{avg_msgs_per_user:.1f}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Avg Messages per User</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error calculating mentor chat metrics: {e}")
    
    # Popular mentors
    st.markdown("### Most Popular Mentors")
    try:
        mentor_popularity = MentorChat.objects.values('mentor__name', 'mentor__type').annotate(
            message_count=Count('id')
        ).order_by('-message_count')[:10]
        
        if mentor_popularity:
            df_mentors = pd.DataFrame(list(mentor_popularity))
            df_mentors['mentor'] = df_mentors['mentor__name'] + ' (' + df_mentors['mentor__type'] + ')'
            
            fig = px.bar(
                df_mentors,
                x='mentor',
                y='message_count',
                labels={'mentor': 'Mentor', 'message_count': 'Messages'},
                title="Most Popular Mentors",
                color='message_count',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_title="Mentor", yaxis_title="Number of Messages")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No mentor chat data available.")
    except Exception as e:
        st.error(f"Error generating popular mentors chart: {e}")
    
    # Chat activity over time
    st.markdown("### Mentor Chat Activity Over Time")
    try:
        # Get chat counts by day for the last 30 days
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
        chat_by_day = MentorChat.objects.filter(
            timestamp__gte=thirty_days_ago
        ).extra(
            select={'day': 'date(timestamp)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        if chat_by_day:
            df_chat = pd.DataFrame(list(chat_by_day))
            df_chat['day'] = pd.to_datetime(df_chat['day'])
            
            fig = px.line(
                df_chat, 
                x='day', 
                y='count',
                labels={'day': 'Date', 'count': 'Message Count'},
                title="Daily Mentor Chat Activity"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chat activity data available for the selected period.")
    except Exception as e:
        st.error(f"Error generating chat activity chart: {e}")

elif page == "Support Issues":
    st.markdown("## Support Issues Analytics")
    
    # Key metrics
    try:
        total_issues = SupportIssue.objects.count()
        open_issues = SupportIssue.objects.filter(status__in=['open', 'in_progress']).count()
        resolved_issues = SupportIssue.objects.filter(status='resolved').count()
        avg_resolution_time = 0  # Would need to calculate from issue history
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{total_issues}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Total Issues</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{open_issues}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Open Issues</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            resolution_rate = (resolved_issues / total_issues * 100) if total_issues > 0 else 0
            st.markdown("<div class='stat-box'>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{resolution_rate:.1f}%</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Resolution Rate</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error calculating support issue metrics: {e}")
    
    # Issues by type and status
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Issues by Type")
        try:
            issue_types = SupportIssue.objects.values('issue_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if issue_types:
                df_types = pd.DataFrame(list(issue_types))
                fig = px.pie(
                    df_types,
                    values='count',
                    names='issue_type',
                    title="Issue Distribution by Type"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No issue type data available.")
        except Exception as e:
            st.error(f"Error generating issue types chart: {e}")
    
    with col2:
        st.markdown("### Issues by Status")
        try:
            issue_status = SupportIssue.objects.values('status').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if issue_status:
                df_status = pd.DataFrame(list(issue_status))
                fig = px.pie(
                    df_status,
                    values='count',
                    names='status',
                    title="Issue Distribution by Status"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No issue status data available.")
        except Exception as e:
            st.error(f"Error generating issue status chart: {e}")
    
    # Issues over time
    st.markdown("### Support Issues Over Time")
    try:
        # Get issue counts by day for the last 90 days
        ninety_days_ago = timezone.now() - datetime.timedelta(days=90)
        issues_by_day = SupportIssue.objects.filter(
            created_at__gte=ninety_days_ago
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        if issues_by_day:
            df_issues = pd.DataFrame(list(issues_by_day))
            df_issues['day'] = pd.to_datetime(df_issues['day'])
            
            fig = px.line(
                df_issues, 
                x='day', 
                y='count',
                labels={'day': 'Date', 'count': 'Issue Count'},
                title="Daily Support Issues"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No issue data available for the selected period.")
    except Exception as e:
        st.error(f"Error generating issues over time chart: {e}")

# Footer
st.markdown("---")
st.markdown("DesiQ Analytics Dashboard | Created with Streamlit")

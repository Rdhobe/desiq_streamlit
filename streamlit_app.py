import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="DesiQ Dashboard",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #424242;
        margin-bottom: 1rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Define the app
def main():
    # Sidebar
    st.sidebar.markdown("## DesiQ Dashboard")
    page = st.sidebar.selectbox(
        "Select a page",
        ["Overview", "Analytics", "Settings"]
    )
    
    # Header
    st.markdown('<div class="main-header">DesiQ Dashboard</div>', unsafe_allow_html=True)
    
    # Page content
    if page == "Overview":
        show_overview()
    elif page == "Analytics":
        show_analytics()
    elif page == "Settings":
        show_settings()

def show_overview():
    st.markdown('<div class="sub-header">Overview</div>', unsafe_allow_html=True)
    
    # Create metrics columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(label="Total Users", value="1,024", delta="12%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(label="Active Sessions", value="142", delta="5%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(label="Conversion Rate", value="24%", delta="-2%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent activity
    st.markdown('<div class="sub-header">Recent Activity</div>', unsafe_allow_html=True)
    
    # Sample data
    data = {
        "Date": ["2023-06-01", "2023-06-02", "2023-06-03", "2023-06-04", "2023-06-05"],
        "User": ["user123", "user456", "user789", "user101", "user202"],
        "Action": ["Login", "Purchase", "Profile Update", "Support Request", "Logout"],
        "Status": ["Success", "Success", "Success", "Pending", "Success"]
    }
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

def show_analytics():
    st.markdown('<div class="sub-header">Analytics</div>', unsafe_allow_html=True)
    
    # Sample data
    chart_data = pd.DataFrame({
        'Date': pd.date_range(start='2023-01-01', periods=30, freq='D'),
        'Users': [100, 120, 110, 130, 140, 120, 110, 100, 90, 110, 120, 130, 150, 140, 130, 
                 120, 110, 100, 90, 95, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
    })
    
    chart_data = chart_data.set_index('Date')
    
    # Line chart
    st.line_chart(chart_data)
    
    # Bar chart data
    bar_data = pd.DataFrame({
        'Category': ['A', 'B', 'C', 'D', 'E'],
        'Values': [20, 40, 30, 50, 45]
    })
    
    st.bar_chart(bar_data.set_index('Category'))
    
    # Map demo
    st.markdown('<div class="sub-header">User Distribution</div>', unsafe_allow_html=True)
    
    map_data = pd.DataFrame({
        'lat': [19.0760, 28.7041, 13.0827, 22.5726, 17.3850],
        'lon': [72.8777, 77.1025, 80.2707, 88.3639, 78.4867]
    })
    
    st.map(map_data)

def show_settings():
    st.markdown('<div class="sub-header">Settings</div>', unsafe_allow_html=True)
    
    with st.form("settings_form"):
        api_url = st.text_input("API URL", "https://api.desiq.live")
        api_key = st.text_input("API Key", type="password")
        theme = st.selectbox("Theme", ["Light", "Dark", "System"])
        notifications = st.checkbox("Enable Notifications")
        
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            st.success("Settings saved successfully!")

# API Connection Example
def fetch_api_data(endpoint, api_key=None):
    """Fetch data from the Django API"""
    base_url = os.environ.get("API_URL", "http://localhost:8000")
    headers = {}
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.get(f"{base_url}{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None

# Run the app
if __name__ == "__main__":
    main() 
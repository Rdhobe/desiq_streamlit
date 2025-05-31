# DesiQ Streamlit Dashboard

This repository contains a Streamlit dashboard for the DesiQ application. The dashboard provides an overview of key metrics, analytics visualizations, and configuration settings.

## Features

- **Overview**: View key metrics and recent activity
- **Analytics**: Visualize user trends and data patterns
- **Settings**: Configure API connections and preferences

## Deployment on Streamlit Cloud

To deploy this application on Streamlit Cloud:

1. Go to [Streamlit Cloud](https://share.streamlit.io/) and sign in
2. Click "New app"
3. Connect your GitHub repository
4. Set the main file path to `streamlit_app.py`
5. Set the Python dependencies file to `streamlit_requirements.txt`
6. (Optional) Configure secrets in the Streamlit Cloud dashboard:
   - API_URL: URL of your DesiQ API backend
   - API_KEY: API key for authentication

## Local Development

To run the application locally:

1. Clone the repository
2. Install the dependencies:
   ```
   pip install -r streamlit_requirements.txt
   ```
3. Create a `.env` file with your environment variables:
   ```
   API_URL=http://localhost:8000
   API_KEY=your_api_key_here
   ```
4. Run the Streamlit application:
   ```
   streamlit run streamlit_app.py
   ```

## Connection to Django Backend

The Streamlit app is designed to connect to the DesiQ Django backend API. The `fetch_api_data()` function demonstrates how to make authenticated API requests to the backend. 
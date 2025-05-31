# DesiQ Streamlit Dashboard

This Streamlit dashboard provides analytics and visualizations for the DesiQ application, helping you understand user behavior, personality test results, scenario performance, and more.

## Prerequisites

- Python 3.7+
- Django project properly configured
- Database with DesiQ data

## Installation

The dashboard uses the dependencies specified in `streamlit_requirements.txt`. You can install them manually or let the run script handle it automatically.

```bash
pip install -r streamlit_requirements.txt
```

## Running the Dashboard

### Option 1: Using the run script (Recommended)

The easiest way to run the dashboard is by using the provided run script:

```bash
python run_streamlit.py
```

This script will:
1. Check if Streamlit is installed and install it if needed
2. Set up the necessary environment variables
3. Start the Streamlit server
4. Open the dashboard in your browser

### Option 2: Running Streamlit directly

You can also run Streamlit directly:

```bash
streamlit run streamlit_app.py
```

## Dashboard Features

The dashboard includes several pages:

1. **Overview**: General platform statistics and metrics
2. **User Analytics**: Detailed user growth, attributes, and behavior
3. **Personality Tests**: Test completion rates and result distributions
4. **Scenarios**: Scenario completion rates and category distributions
5. **Mentor Chats**: Mentor popularity and chat activity
6. **Support Issues**: Issue tracking and resolution metrics

## Troubleshooting

If you encounter any issues:

1. **Django Connection Error**: Make sure your Django project is properly configured and the `desiq/settings.py` file is accessible.

2. **Database Connection Error**: Verify that your database settings are correct in the Django settings.

3. **Missing Dependencies**: If you see import errors, try running:
   ```bash
   pip install -r streamlit_requirements.txt
   ```

4. **Port Already in Use**: If port 8501 is already in use, you can specify a different port:
   ```bash
   streamlit run streamlit_app.py --server.port 8502
   ```

## Note on Data Refresh

The dashboard pulls data directly from your Django database in real-time, so any updates to your database will be reflected in the dashboard on page refresh. 
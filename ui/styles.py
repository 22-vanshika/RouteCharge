import streamlit as st

def inject_styles() -> None:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Force Global Light Theme Theme Variables */
        :root, .stApp {
            --background-color: #ffffff !important;
            --secondary-background-color: #f8f9fa !important;
            --text-color: #1a1c23 !important;
            --primary-color: #4e8cff !important;
            
            background-color: #ffffff !important;
            color: #1a1c23 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* Override App & Header containers */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
            background-color: #ffffff !important;
            color: #1a1c23 !important;
        }

        /* Sidebar forced light theme */
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
            background-color: #f8f9fa !important;
            border-right: 1px solid #dee2e6 !important;
        }

        [data-testid="stSidebar"] * {
            color: #1a1c23 !important;
        }

        /* Force Selectboxes, Dropdowns and Option Lists to be White Background & Dark Text */
        div[data-baseweb="select"], div[data-baseweb="select"] *, div[role="listbox"], li[role="option"] {
            background-color: #ffffff !important;
            color: #1a1c23 !important;
        }
        
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #f1f3f5 !important;
            color: #1a1c23 !important;
        }

        div[role="listbox"] {
            background-color: #ffffff !important;
            border: 1px solid #dee2e6 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
        }

        /* Override select input value specifically */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #1a1c23 !important;
            border-color: #dee2e6 !important;
        }

        /* Global Headers Override */
        h1, h2, h3, h4, h5, h6, .main h1, [data-testid="stSidebar"] h1 {
            color: #1a1c23 !important;
            margin-bottom: 8px !important;
            font-weight: 700 !important;
        }

        /* Hero Title Visibility - Main Content Only */
        .main h1 {
            font-size: 2.75rem !important;
            font-weight: 800 !important;
            margin-bottom: 24px !important;
            letter-spacing: -0.8px !important;
            line-height: 1.2 !important;
        }

        /* Base Metric Card Customization - Force Light Theme */
        div[data-testid="stMetric"] {
            background-color: #f8f9fa !important;
            padding: 16px 20px !important;
            border-radius: 8px !important;
            border: 1px solid #dee2e6 !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04) !important;
            min-height: 100px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            font-weight: 700 !important;
            color: #1a1c23 !important;
            margin-top: 4px !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            color: #495057 !important;
            opacity: 1 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }

        /* Modern Tab Pill Bar - Force Light Theme */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px !important;
            background-color: #f1f3f5 !important;
            padding: 6px !important;
            border-radius: 8px !important;
            border: 1px solid #dee2e6 !important;
        }

        .stTabs [data-baseweb="tab"] {
            height: 40px !important;
            white-space: pre-wrap !important;
            background-color: transparent !important;
            border-radius: 6px !important;
            padding: 0px 16px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            color: #495057 !important;
            border: none !important;
            opacity: 0.8 !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(0, 0, 0, 0.04) !important;
            opacity: 1 !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: #4e8cff !important;
            color: #ffffff !important;
            box-shadow: 0 2px 6px rgba(78, 140, 255, 0.25) !important;
            opacity: 1 !important;
        }

        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        /* Sidebar Styling Refinements */
        [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            color: #1a1c23 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            margin-bottom: 6px !important;
        }

        [data-testid="stSidebar"] hr {
            margin-top: 16px !important;
            margin-bottom: 16px !important;
            border-color: #dee2e6 !important;
        }

        /* Ensure all general text and labels are styled crisp dark black */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #1a1c23 !important;
        }

        /* Override Streamlit Sliders and Tooltips for Light Theme styling */
        div[data-testid="stSlider"] * {
            color: #1a1c23 !important;
        }

        /* Hide hamburger/settings menu completely to remove theme toggle options */
        #MainMenu, [data-testid="stMainMenu"], button[data-testid="stMainMenu"] {
            display: none !important;
            visibility: hidden !important;
        }
        </style>
    """, unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
import json
import numpy as np
import re
from scraper import scrape_all_sources, get_source_urls
from data_processor import process_data, analyze_keywords, analyze_sentiment, generate_wordcloud, analyze_attack_types
from visualizer import plot_news_by_source, plot_news_by_date, plot_sentiment_analysis, plot_keyword_distribution, plot_attack_types
from utils import filter_dataframe, download_data, load_data, save_data
from alert_system import (
    register_phone_for_alerts, get_registered_phone, test_alert_system, 
    check_for_alerts, run_alert_system, get_critical_news_digest,
    send_digest_alert
)

# Set page configuration
st.set_page_config(
    page_title="Indian Cybersecurity News Tracker",
    page_icon="🔒",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'data' not in st.session_state:
    st.session_state.data = None
if 'last_scraped' not in st.session_state:
    st.session_state.last_scraped = None
if 'keywords' not in st.session_state:
    st.session_state.keywords = None
if 'sentiment_data' not in st.session_state:
    st.session_state.sentiment_data = None
if 'attack_types' not in st.session_state:
    st.session_state.attack_types = None
if 'critical_alerts' not in st.session_state:
    st.session_state.critical_alerts = []
if 'alert_sent' not in st.session_state:
    st.session_state.alert_sent = False

# Title
st.title("🔒 Indian Cybersecurity News Tracker")
st.subheader("Track, analyze, and visualize cybersecurity news from Indian sources")

# Sidebar
st.sidebar.header("Controls")

# Data loading and scraping options
data_option = st.sidebar.radio(
    "Choose data source:",
    ("Load previous data", "Scrape new data")
)

if data_option == "Load previous data":
    if os.path.exists("cybersecurity_news.csv"):
        st.session_state.data = load_data("cybersecurity_news.csv")
        with st.sidebar.expander("Data loaded successfully"):
            st.write(f"Loaded {len(st.session_state.data)} news articles")
    else:
        st.sidebar.warning("No previous data found. Please scrape new data.")
        data_option = "Scrape new data"

if data_option == "Scrape new data":
    scrape_button = st.sidebar.button("Start Scraping")
    
    if scrape_button:
        # Create a progress container
        progress_container = st.empty()
        progress_container.info("Initializing scraping process...")
        
        source_urls = get_source_urls()
        sources_text = "\n".join([f"- {src}" for src in source_urls.keys()])
        st.info(f"Attempting to scrape from:\n{sources_text}")
        
        # Create a placeholder for scraping status
        status_container = st.empty()
        status_container.info("Starting to scrape sources...")
        
        # Perform scraping with detailed logging
        raw_data = scrape_all_sources()
        
        # Show scraping results
        if raw_data:
            # Process the scraped data
            progress_container.info("Processing scraped data...")
            processed_data = process_data(raw_data)
            
            # Save and store the data
            progress_container.info("Saving data...")
            save_data(processed_data, "cybersecurity_news.csv")
            st.session_state.data = processed_data
            
            # Calculate sources
            sources = processed_data['source'].value_counts().to_dict()
            
            # Display results by source
            result_text = "### Scraping Results\n"
            for source, count in sources.items():
                status = "✅" if count > 0 else "❌"
                result_text += f"{status} **{source}**: {count} articles\n"
            
            status_container.markdown(result_text)
            
            # Record timestamp and run analysis
            st.session_state.last_scraped = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Extract keywords, sentiment and attack types
            progress_container.info("Analyzing keywords and sentiment...")
            st.session_state.keywords = analyze_keywords(processed_data)
            st.session_state.sentiment_data = analyze_sentiment(processed_data)
            
            progress_container.info("Analyzing attack types...")
            st.session_state.attack_types = analyze_attack_types(processed_data)
            
            # Automatically check for critical security alerts and send notifications
            registered_phone = get_registered_phone()
            if registered_phone:
                progress_container.info("Checking for critical security alerts...")
                critical_items, alert_sent = run_alert_system(processed_data)
                st.session_state.critical_alerts = critical_items
                st.session_state.alert_sent = alert_sent
                
                if critical_items:
                    if alert_sent:
                        status_container.success(f"Found {len(critical_items)} critical security alerts. SMS notifications sent to {registered_phone}.")
                    else:
                        status_container.warning(f"Found {len(critical_items)} critical security alerts, but could not send SMS notifications. Check Twilio credentials.")
            
            # Show success message
            progress_container.success(f"Scraping complete! Retrieved {len(processed_data)} articles from {len(sources)} sources.")
            st.rerun()
        else:
            # Show error message
            progress_container.error("No data retrieved from any source. Check the logs for details.")
            status_container.markdown("### Scraping failed for all sources\nCheck each source for potential issues.")

# Main content area (only show if data is available)
if st.session_state.data is not None:
    df = st.session_state.data
    
    # Data info section
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total News Articles", len(df))
    with col2:
        st.metric("Sources", df['source'].nunique())
    with col3:
        if st.session_state.last_scraped:
            st.metric("Last Updated", st.session_state.last_scraped)
    
    # Filter section
    with st.expander("Filter Data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_sources = st.multiselect(
                "Select Sources",
                options=sorted(df['source'].unique()),
                default=sorted(df['source'].unique())
            )
        with col2:
            # Ensure dates are proper datetime dates for the date_input widget
            min_date = df['date'].min().date() if isinstance(df['date'].min(), pd.Timestamp) else df['date'].min()
            max_date = df['date'].max().date() if isinstance(df['date'].max(), pd.Timestamp) else df['date'].max()
            
            date_range = st.date_input(
                "Select Date Range",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
        
        search_term = st.text_input("Search in Headlines", "")
        
        # Apply filters
        filtered_df = filter_dataframe(df, selected_sources, date_range, search_term)
        
        st.write(f"Showing {len(filtered_df)} of {len(df)} articles")
    
    # Display filtered data
    st.subheader("Recent News Articles")
    st.dataframe(
        filtered_df[['headline', 'source', 'date', 'url']].sort_values('date', ascending=False),
        use_container_width=True,
        hide_index=True
    )
    
    # Download option
    download_data(filtered_df, "indian_cybersecurity_news.csv")
    
    # Visualizations
    st.header("Visualizations and Insights")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Source Distribution", "Time Trends", "Sentiment Analysis", "Keyword Analysis", "Attack Types"])
    
    with tab1:
        st.subheader("News Distribution by Source")
        fig = plot_news_by_source(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("News Trends Over Time")
        fig = plot_news_by_date(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Sentiment Analysis")
        if st.session_state.sentiment_data is not None:
            # Filter sentiment data
            filtered_sentiment = st.session_state.sentiment_data[
                st.session_state.sentiment_data['headline'].isin(filtered_df['headline'])
            ]
            fig = plot_sentiment_analysis(filtered_sentiment)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display average sentiment by source
            st.subheader("Average Sentiment by Source")
            source_sentiment = filtered_sentiment.groupby('source')['polarity'].mean().reset_index()
            source_sentiment = source_sentiment.rename(columns={'polarity': 'sentiment_score'})
            fig = px.bar(
                source_sentiment, 
                x='source', 
                y='sentiment_score',
                color='sentiment_score',
                color_continuous_scale=['red', 'yellow', 'green'],
                title="Average Sentiment Score by Source",
                labels={'sentiment_score': 'Sentiment Score (-1 to 1)'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sentiment data not available. Please run sentiment analysis.")
    
    with tab4:
        st.subheader("Keyword Analysis")
        if st.session_state.keywords is not None:
            # Get top keywords
            keyword_counts = st.session_state.keywords
            fig = plot_keyword_distribution(keyword_counts)
            st.plotly_chart(fig, use_container_width=True)
            
            # Generate word cloud
            st.subheader("Word Cloud of Key Terms")
            wc_image = generate_wordcloud(filtered_df)
            st.image(wc_image)
        else:
            st.info("Keyword data not available. Please run keyword analysis.")
    
    with tab5:
        st.subheader("Cyber Attack Types Analysis")
        if st.session_state.attack_types is not None:
            # Get attack type analysis
            st.write("This visualization shows the distribution of cyber attack types mentioned in news articles.")
            
            # If we need to reanalyze for the filtered dataset
            if st.checkbox("Analyze attack types in filtered dataset only", value=False):
                st.info("Analyzing attack types in filtered data...")
                filtered_attack_df = analyze_attack_types(filtered_df)
                fig = plot_attack_types(filtered_attack_df)
            else:
                # Use the pre-analyzed attack types
                fig = plot_attack_types(st.session_state.attack_types)
                
            st.plotly_chart(fig, use_container_width=True)
            
            # Add some insights about attack types
            st.subheader("Attack Type Insights")
            
            if len(st.session_state.attack_types) > 0:
                top_attack = st.session_state.attack_types.iloc[0]['attack_type']
                top_attack_count = st.session_state.attack_types.iloc[0]['count']
                
                st.markdown(f"""
                #### Key Findings:
                - **Most common attack type:** {top_attack} ({top_attack_count} mentions)
                - **Total attack types identified:** {len(st.session_state.attack_types)}
                
                These insights can help organizations prioritize their cybersecurity defenses based on the most prevalent threats in the news.
                """)
            else:
                st.info("No attack types detected in the dataset.")
        else:
            st.info("Attack type data not available. Please scrape new data to analyze attack types.")

    # Article details view
    if len(filtered_df) > 0:
        st.header("Article Details")
        selected_article = st.selectbox(
            "Select an article to view details",
            filtered_df['headline'].tolist()
        )
        
        if selected_article:
            article = filtered_df[filtered_df['headline'] == selected_article].iloc[0]
            
            st.subheader(article['headline'])
            st.write(f"**Source:** {article['source']} | **Date:** {article['date'].strftime('%Y-%m-%d')}")
            
            if 'content' in article and article['content']:
                st.write("**Summary:**")
                st.write(article['content'][:500] + "..." if len(article['content']) > 500 else article['content'])
            
            st.write(f"[Read Full Article]({article['url']})")
else:
    st.info("No data available. Please load previous data or scrape new data using the sidebar options.")

# Security Alert System
st.header("🚨 Critical Security Alerts")

# Create a tab layout for the alert system
alert_tab1, alert_tab2 = st.tabs(["Alert Setup", "Critical News"])

with alert_tab1:
    st.subheader("Register for SMS Alerts")
    st.write("""
    Get instant SMS notifications for critical cybersecurity alerts from government sources.
    This feature uses Twilio to send SMS messages to your registered phone number.
    """)
    
    # Show currently registered phone (if any)
    current_phone = get_registered_phone()
    if current_phone:
        st.success(f"Currently registered phone number: {current_phone}")
    
    # Phone number registration
    with st.form("phone_registration_form"):
        phone_number = st.text_input(
            "Enter your phone number (with country code)",
            placeholder="+91XXXXXXXXXX",
            help="Include your country code (e.g., +91 for India)"
        )
        
        col1, col2 = st.columns(2)
        register_submitted = col1.form_submit_button("Register Phone")
        test_submitted = col2.form_submit_button("Test Alert")
    
    # Handle form submission for registration
    if register_submitted and phone_number:
        success, message = register_phone_for_alerts(phone_number)
        if success:
            st.success(message)
        else:
            st.error(message)
    
    # Handle form submission for test alert
    if test_submitted:
        phone_to_test = current_phone or phone_number
        if phone_to_test:
            with st.spinner("Sending test alert..."):
                success, message = test_alert_system(phone_to_test)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.error("No phone number provided for testing")
    
    # Alert settings
    st.subheader("Alert Settings")
    with st.expander("Configure Alert Settings", expanded=False):
        st.write("""
        The system automatically detects critical cybersecurity news using these criteria:
        - High-priority sources (CERT-In, NCIIPC, I4C, NASSCOM) with high-severity keywords
        - High-priority sources with multiple medium-severity keywords
        - Medium-priority sources (major news outlets) with high-severity keywords
        - Any news with combinations of high and medium severity keywords
        - Any news with multiple security-related keywords (3+)
        """)
        
        # Show the keywords that trigger alerts by severity
        st.write("#### Critical Keywords by Severity:")
        
        st.write("**High Severity:**")
        high_cols = st.columns(3)
        high_keywords = [
            'critical', 'urgent', 'emergency', 'severe', 'zero-day', 
            'ransomware', 'remote code execution', 'data breach', 'national security'
        ]
        for i, keyword in enumerate(high_keywords):
            high_cols[i % 3].markdown(f"- {keyword}")
        
        st.write("**Medium Severity:**")
        med_cols = st.columns(3)
        medium_keywords = [
            'vulnerability', 'exploit', 'breach', 'attack', 'compromise', 'warning',
            'malware', 'backdoor', 'data leak', 'hack', 'phishing campaign'
        ]
        for i, keyword in enumerate(medium_keywords):
            med_cols[i % 3].markdown(f"- {keyword}")
            
        st.write("**Low Severity:**")
        low_cols = st.columns(3)
        low_keywords = [
            'alert', 'security update', 'patch', 'advisory', 'update available',
            'security issue', 'cybersecurity', 'threat'
        ]
        for i, keyword in enumerate(low_keywords):
            low_cols[i % 3].markdown(f"- {keyword}")
            
        # Add auto-alert explanation
        st.write("""
        #### Automatic Alert System
        
        When new data is scraped, the system:
        1. Automatically analyzes all new articles for critical security issues
        2. Identifies high-priority news items using the criteria above
        3. Immediately sends SMS alerts for critical news to your registered phone
        4. Saves alert history to prevent duplicate notifications
        """)
        
        if not get_registered_phone():
            st.warning("⚠️ No phone number registered. Please register a phone number above to receive automatic alerts.")

with alert_tab2:
    st.subheader("Critical Security News")
    
    # Create columns for the two button options
    col1, col2 = st.columns(2)
    
    # Button to check for critical alerts
    if col1.button("Check for Critical Alerts Now"):
        if st.session_state.data is not None:
            with st.spinner("Analyzing news for critical security threats..."):
                critical_items, alert_sent = check_for_alerts(st.session_state.data, get_registered_phone())
                st.session_state.critical_alerts = critical_items
                st.session_state.alert_sent = alert_sent
                
                if critical_items:
                    if alert_sent:
                        st.success(f"Found {len(critical_items)} critical security alerts. SMS notifications sent.")
                    else:
                        st.warning(f"Found {len(critical_items)} critical security alerts, but could not send SMS notifications. Please check your phone number registration.")
                else:
                    st.info("No critical security alerts found in the current data.")
        else:
            st.error("No data available. Please load or scrape news data first.")
    
    # Button for sending a security digest
    if col2.button("Send Security Digest"):
        if st.session_state.data is not None:
            with st.spinner("Generating security digest..."):
                phone_number = get_registered_phone()
                if phone_number:
                    # Get the top critical news items by score
                    digest_items = get_critical_news_digest(st.session_state.data, max_items=5)
                    
                    if digest_items:
                        # Send the digest
                        success = send_digest_alert(phone_number, digest_items)
                        if success:
                            st.success(f"Security digest with top {len(digest_items)} critical items sent to {phone_number}")
                        else:
                            st.error("Failed to send security digest. Check Twilio credentials.")
                        
                        # Store in session state to display
                        st.session_state.critical_alerts = digest_items
                    else:
                        st.info("No critical security items found for the digest.")
                else:
                    st.error("No phone number registered for alerts. Please register a phone number first.")
        else:
            st.error("No data available. Please load or scrape news data first.")
    
    # Display critical alerts with severity scores
    if st.session_state.critical_alerts:
        st.write(f"Found {len(st.session_state.critical_alerts)} critical security alerts:")
        
        # Sort by criticality score if available
        sorted_items = st.session_state.critical_alerts
        if 'criticality_score' in sorted_items[0]:
            sorted_items = sorted(sorted_items, key=lambda x: x.get('criticality_score', 0), reverse=True)
        
        for i, item in enumerate(sorted_items):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{i+1}. {item['headline']}**")
                    score_text = f" | Severity: {item['criticality_score']}" if 'criticality_score' in item else ""
                    st.markdown(f"Source: **{item['source']}** | Date: {item['date']}{score_text}")
                    
                with col2:
                    if 'url' in item and item['url']:
                        st.markdown(f"[Read Full Article]({item['url']})")
                
                # Show a preview of the content
                if 'content' in item and item['content']:
                    with st.expander("Show details"):
                        st.write(item['content'][:300] + "..." if len(item['content']) > 300 else item['content'])
                
                st.divider()
    else:
        st.info("No critical security alerts detected. Check back after scraping new data or click one of the buttons above to check current data.")
    
    # Add explanation about the difference between regular alerts and digest
    with st.expander("About Security Alerts vs. Security Digest"):
        st.write("""
        ### Alert Types
        
        **Individual Alerts** (Check for Critical Alerts Now):
        - Checks for critical items using keyword and source-based criteria
        - Sends individual SMS notifications for each critical item
        - Good for immediate notification about specific security issues
        
        **Security Digest** (Send Security Digest):
        - Uses a scoring system to rank news items by criticality
        - Combines the top items into a single SMS message
        - Useful for getting a summary of the most important security news
        
        Both options will only send alerts to your registered phone number.
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center">
        <p>Developed for Indian Cybersecurity News Analysis | Data sourced from various Indian cybersecurity news sources</p>
    </div>
    """,
    unsafe_allow_html=True
)

import pandas as pd
import datetime
import streamlit as st
import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def filter_dataframe(df, sources=None, date_range=None, search_term=None):
    """
    Filter DataFrame based on selected sources, date range, and search term.
    
    Args:
        df: DataFrame to filter
        sources: List of sources to include
        date_range: Tuple of (start_date, end_date)
        search_term: String to search in headlines
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    # Filter by source
    if sources and len(sources) > 0:
        filtered_df = filtered_df[filtered_df['source'].isin(sources)]
    
    # Filter by date range
    if date_range and len(date_range) == 2:
        try:
            start_date, end_date = date_range
            
            # Make sure the dates in DataFrame are datetime objects
            if not pd.api.types.is_datetime64_any_dtype(filtered_df['date']):
                filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Convert input dates to Timestamps for comparison
            start_date_ts = pd.Timestamp(start_date)
            end_date_ts = pd.Timestamp(end_date)
            
            # Filter by date range
            filtered_df = filtered_df[
                (filtered_df['date'] >= start_date_ts) &
                (filtered_df['date'] <= end_date_ts)
            ]
        except Exception as e:
            logger.error(f"Error filtering by date range: {str(e)}")
            # Skip date filtering if there's an error
    
    # Filter by search term
    if search_term and search_term.strip():
        filtered_df = filtered_df[
            filtered_df['headline'].str.contains(search_term, case=False, na=False)
        ]
    
    return filtered_df

def download_data(df, filename="cybersecurity_news.csv"):
    """
    Add a download button for the DataFrame
    
    Args:
        df: DataFrame to download
        filename: Name of the file to download
    """
    # Convert DataFrame to CSV
    csv = df.to_csv(index=False)
    
    # Create download button
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

def save_data(df, filename="cybersecurity_news.csv"):
    """
    Save DataFrame to CSV file
    
    Args:
        df: DataFrame to save
        filename: Name of the file to save
    """
    try:
        df.to_csv(filename, index=False)
        logger.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {str(e)}")
        return False

def load_data(filename="cybersecurity_news.csv"):
    """
    Load DataFrame from CSV file
    
    Args:
        filename: Name of the file to load
        
    Returns:
        DataFrame or None if file not found
    """
    try:
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            
            # Convert date column to datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            logger.info(f"Data loaded from {filename}")
            return df
        else:
            logger.warning(f"File {filename} not found")
            return None
    except Exception as e:
        logger.error(f"Error loading data from {filename}: {str(e)}")
        return None

def format_date(date_obj):
    """
    Format date object to string
    
    Args:
        date_obj: Date object to format
        
    Returns:
        Formatted date string
    """
    if isinstance(date_obj, (datetime.date, datetime.datetime)):
        return date_obj.strftime("%Y-%m-%d")
    elif isinstance(date_obj, pd.Timestamp):
        return date_obj.strftime("%Y-%m-%d")
    else:
        return str(date_obj)

def parse_date(date_str):
    """
    Parse date string to date object
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Date object
    """
    try:
        return pd.to_datetime(date_str).date()
    except:
        logger.warning(f"Failed to parse date: {date_str}")
        return datetime.date.today()

def get_date_range(df, default_days=30):
    """
    Get the date range for the DataFrame
    
    Args:
        df: DataFrame to get date range from
        default_days: Number of days to show by default
        
    Returns:
        Tuple of (start_date, end_date)
    """
    if 'date' not in df.columns or df.empty:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=default_days)
        return (start_date, end_date)
    
    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Get min and max dates
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    # If range is less than default_days, expand to default_days
    if (max_date - min_date).days < default_days:
        start_date = max_date - datetime.timedelta(days=default_days)
        # But don't go earlier than min_date
        start_date = max(start_date, min_date)
    else:
        start_date = min_date
    
    return (start_date, max_date)

def clean_text(text):
    """
    Clean text for display
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Remove excessive newlines and spaces
    text = ' '.join(text.split())
    
    return text

def truncate_text(text, max_length=200):
    """
    Truncate text to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length of the text
        
    Returns:
        Truncated text
    """
    if not text or not isinstance(text, str):
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."

if __name__ == "__main__":
    # For testing
    try:
        # Create test DataFrame
        data = {
            'headline': ['Test headline 1', 'Test headline 2', 'Test headline 3'],
            'source': ['Source A', 'Source B', 'Source A'],
            'date': [datetime.date(2023, 1, 1), datetime.date(2023, 1, 2), datetime.date(2023, 1, 3)],
            'content': ['Test content 1', 'Test content 2', 'Test content 3'],
            'url': ['http://example.com/1', 'http://example.com/2', 'http://example.com/3']
        }
        df = pd.DataFrame(data)
        
        # Test save and load
        save_data(df, "test_data.csv")
        loaded_df = load_data("test_data.csv")
        
        if loaded_df is not None:
            print("Data saved and loaded successfully")
            print(f"Original shape: {df.shape}, Loaded shape: {loaded_df.shape}")
        
        # Test filtering
        filtered_df = filter_dataframe(df, sources=['Source A'])
        print(f"Filtered shape: {filtered_df.shape}")
        
        # Clean up test file
        try:
            os.remove("test_data.csv")
        except:
            pass
    except Exception as e:
        print(f"Error in testing: {str(e)}")

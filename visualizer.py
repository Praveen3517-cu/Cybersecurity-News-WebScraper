import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def plot_news_by_source(df):
    """Create a bar chart showing the distribution of news by source"""
    logger.info("Creating news by source visualization")
    
    # Count news by source
    source_counts = df['source'].value_counts().reset_index()
    source_counts.columns = ['source', 'count']
    
    # Create bar chart
    fig = px.bar(
        source_counts,
        x='source',
        y='count',
        color='source',
        title="News Distribution by Source",
        labels={'count': 'Number of Articles', 'source': 'Source'}
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Source",
        yaxis_title="Number of Articles",
        legend_title="Source",
        plot_bgcolor='rgba(0,0,0,0)',
        height=500
    )
    
    return fig

def plot_news_by_date(df):
    """Create a line chart showing the trend of news over time"""
    logger.info("Creating news by date visualization")
    
    # Ensure date is in datetime format
    df['date'] = pd.to_datetime(df['date'])
    
    # Count news by date
    date_counts = df.groupby(df['date'].dt.date).size().reset_index(name='count')
    date_counts.columns = ['date', 'count']
    
    # Sort by date
    date_counts = date_counts.sort_values('date')
    
    # Create line chart
    fig = px.line(
        date_counts,
        x='date',
        y='count',
        title="News Trend Over Time",
        labels={'count': 'Number of Articles', 'date': 'Date'}
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Articles",
        plot_bgcolor='rgba(0,0,0,0)',
        height=500
    )
    
    # Add markers for data points
    fig.update_traces(mode='lines+markers')
    
    # Add source breakdown if available
    if len(df['source'].unique()) > 1:
        source_date_counts = df.groupby([df['date'].dt.date, 'source']).size().reset_index(name='count')
        source_date_counts.columns = ['date', 'source', 'count']
        
        # Add a line for each source
        for source in df['source'].unique():
            source_data = source_date_counts[source_date_counts['source'] == source]
            
            if not source_data.empty:
                fig.add_trace(
                    go.Scatter(
                        x=source_data['date'],
                        y=source_data['count'],
                        mode='lines+markers',
                        name=source,
                        line=dict(width=1),
                        marker=dict(size=6)
                    )
                )
    
    return fig

def plot_sentiment_analysis(sentiment_df):
    """Create visualizations for sentiment analysis"""
    logger.info("Creating sentiment analysis visualization")
    
    # Count sentiment categories
    sentiment_counts = sentiment_df['sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['sentiment', 'count']
    
    # Create color map
    color_map = {
        'Positive': 'green',
        'Neutral': 'blue',
        'Negative': 'red'
    }
    
    # Create the pie chart
    fig = px.pie(
        sentiment_counts, 
        values='count', 
        names='sentiment',
        title='Sentiment Distribution of News Articles',
        color='sentiment',
        color_discrete_map=color_map
    )
    
    # Update layout
    fig.update_layout(
        legend_title="Sentiment",
        plot_bgcolor='rgba(0,0,0,0)',
        height=500
    )
    
    # Update traces
    fig.update_traces(textinfo='percent+label')
    
    return fig

def plot_sentiment_over_time(sentiment_df):
    """Create a line chart showing sentiment trends over time"""
    logger.info("Creating sentiment over time visualization")
    
    # Ensure date is in datetime format
    sentiment_df['date'] = pd.to_datetime(sentiment_df['date'])
    
    # Group by date and get average polarity
    sentiment_time = sentiment_df.groupby(sentiment_df['date'].dt.date)['polarity'].mean().reset_index()
    sentiment_time.columns = ['date', 'avg_polarity']
    
    # Sort by date
    sentiment_time = sentiment_time.sort_values('date')
    
    # Create line chart
    fig = px.line(
        sentiment_time,
        x='date',
        y='avg_polarity',
        title="Sentiment Trend Over Time",
        labels={'avg_polarity': 'Average Sentiment (Polarity)', 'date': 'Date'}
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Average Sentiment (Polarity)",
        plot_bgcolor='rgba(0,0,0,0)',
        height=500
    )
    
    # Add horizontal line at zero
    fig.add_shape(
        type='line',
        x0=sentiment_time['date'].min(),
        x1=sentiment_time['date'].max(),
        y0=0,
        y1=0,
        line=dict(color='gray', dash='dash')
    )
    
    # Add markers for data points
    fig.update_traces(mode='lines+markers')
    
    # Add color to line based on polarity
    fig.update_traces(
        line=dict(
            color='green',
            width=3
        ),
        marker=dict(
            size=8,
            color=sentiment_time['avg_polarity'].apply(
                lambda x: 'green' if x > 0 else 'red' if x < 0 else 'blue'
            )
        )
    )
    
    return fig

def plot_keyword_distribution(keyword_counts):
    """Create a bar chart showing the distribution of top keywords"""
    logger.info("Creating keyword distribution visualization")
    
    # Convert dictionary to DataFrame
    df = pd.DataFrame(list(keyword_counts.items()), columns=['keyword', 'count'])
    
    # Sort by count and take top 20
    df = df.sort_values('count', ascending=False).head(20)
    
    # Create bar chart
    fig = px.bar(
        df,
        x='keyword',
        y='count',
        title="Top 20 Keywords in Cybersecurity News",
        labels={'count': 'Frequency', 'keyword': 'Keyword'}
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Keyword",
        yaxis_title="Frequency",
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        xaxis={'categoryorder':'total descending'}
    )
    
    # Update trace appearance
    fig.update_traces(
        marker_color='royalblue',
        texttemplate='%{y}',
        textposition='outside'
    )
    
    # Rotate x-axis labels for better readability
    fig.update_layout(xaxis_tickangle=-45)
    
    return fig

def plot_source_reliability(df):
    """Create a visualization that shows the reliability or bias of news sources"""
    logger.info("Creating source reliability visualization")
    
    # Count news sources
    source_counts = df['source'].value_counts().reset_index()
    source_counts.columns = ['source', 'total_articles']
    
    # This is a simplified metric - in a real app, you could have actual reliability metrics
    # Here we're using a random reliability score for demonstration
    np.random.seed(42)  # For reproducibility
    source_counts['reliability_score'] = np.random.uniform(0.7, 0.95, len(source_counts))
    
    # Create scatter plot
    fig = px.scatter(
        source_counts,
        x='total_articles',
        y='reliability_score',
        size='total_articles',
        color='source',
        text='source',
        title="Source Reliability vs. Volume",
        labels={
            'total_articles': 'Number of Articles',
            'reliability_score': 'Reliability Score',
            'source': 'Source'
        },
        size_max=50
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Number of Articles",
        yaxis_title="Reliability Score",
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        yaxis=dict(range=[0.65, 1.0])
    )
    
    # Update trace appearance
    fig.update_traces(
        textposition='top center',
        marker=dict(opacity=0.8)
    )
    
    # Add a helper line for the average reliability
    avg_reliability = source_counts['reliability_score'].mean()
    fig.add_shape(
        type='line',
        x0=0,
        x1=source_counts['total_articles'].max() * 1.1,
        y0=avg_reliability,
        y1=avg_reliability,
        line=dict(color='gray', dash='dash')
    )
    
    fig.add_annotation(
        x=source_counts['total_articles'].max() * 0.1,
        y=avg_reliability + 0.01,
        text=f"Average Reliability: {avg_reliability:.2f}",
        showarrow=False,
        bgcolor="white",
        bordercolor="gray",
        borderwidth=1
    )
    
    return fig

def plot_attack_types(attack_df):
    """Create a visualization showing the distribution of attack types mentioned in news"""
    logger.info("Creating attack types visualization")
    
    if attack_df is None or len(attack_df) == 0:
        # Create empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No attack types detected in the data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Color map for different attack types
    color_map = {
        'Phishing': '#ff7f0e',  # Orange
        'Ransomware': '#d62728',  # Red
        'Malware': '#9467bd',  # Purple
        'Data Breach': '#1f77b4',  # Blue
        'DDoS': '#2ca02c',  # Green
        'Social Engineering': '#e377c2',  # Pink
        'Identity Theft': '#8c564b',  # Brown
        'Zero-day': '#bcbd22',  # Olive
        'Supply Chain': '#17becf',  # Cyan
        'IoT Attacks': '#7f7f7f'   # Gray
    }
    
    # Create bar chart with custom colors
    fig = px.bar(
        attack_df,
        x='attack_type',
        y='count',
        color='attack_type',
        title="Cyber Attack Types Mentioned in News",
        labels={'count': 'Number of Mentions', 'attack_type': 'Attack Type'},
        color_discrete_map=color_map
    )
    
    # Update layout for better appearance
    fig.update_layout(
        xaxis_title="Attack Type",
        yaxis_title="Number of Mentions",
        xaxis_tickangle=-45,
        height=600,
        bargap=0.2,
        legend_title="Attack Types",
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={'categoryorder':'total descending'}
    )
    
    return fig

def plot_threat_category_distribution(df):
    """Create a visualization showing the distribution of threat categories"""
    logger.info("Creating threat category distribution visualization")
    
    # Define threat categories and their related keywords
    threat_categories = {
        'Ransomware': ['ransomware', 'ransom', 'encrypt', 'decrypt', 'crypto locker'],
        'Data Breach': ['breach', 'leak', 'exposed', 'compromise', 'stolen data'],
        'Phishing': ['phish', 'spoof', 'email scam', 'credential harvest'],
        'Malware': ['malware', 'virus', 'trojan', 'worm', 'spyware'],
        'DDoS': ['ddos', 'denial of service', 'botnet', 'traffic flood'],
        'Social Engineering': ['social engineering', 'pretexting', 'baiting', 'quid pro quo'],
        'Zero-day': ['zero-day', '0-day', 'unpatched', 'vulnerability', 'exploit'],
        'Insider Threat': ['insider', 'employee', 'privileged user', 'access abuse'],
        'Supply Chain': ['supply chain', 'third party', 'vendor', 'software supply']
    }
    
    # Initialize category counts
    category_counts = {category: 0 for category in threat_categories}
    
    # Count mentions of each category
    for _, row in df.iterrows():
        content = f"{row['headline']} {row['content']}".lower()
        
        for category, keywords in threat_categories.items():
            for keyword in keywords:
                if keyword.lower() in content:
                    category_counts[category] += 1
                    break  # Count only once per article per category
    
    # Convert to DataFrame
    threat_df = pd.DataFrame(list(category_counts.items()), columns=['category', 'count'])
    threat_df = threat_df.sort_values('count', ascending=False)
    
    # Create bar chart
    fig = px.bar(
        threat_df,
        x='category',
        y='count',
        color='category',
        title="Distribution of Cybersecurity Threat Categories",
        labels={'count': 'Number of Mentions', 'category': 'Threat Category'}
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Threat Category",
        yaxis_title="Number of Mentions",
        legend_title="Threat Category",
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        xaxis={'categoryorder':'total descending'}
    )
    
    return fig

if __name__ == "__main__":
    # For testing
    try:
        df = pd.read_csv("cybersecurity_news.csv")
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Test plot_news_by_source
        fig1 = plot_news_by_source(df)
        print("Created news by source visualization")
        
        # Test plot_news_by_date
        fig2 = plot_news_by_date(df)
        print("Created news by date visualization")
        
        # Create dummy sentiment data for testing
        sentiments = ['Positive', 'Neutral', 'Negative']
        sentiment_data = []
        
        for _, row in df.iterrows():
            sentiment_data.append({
                'headline': row['headline'],
                'source': row['source'],
                'date': row['date'],
                'sentiment': np.random.choice(sentiments),
                'polarity': np.random.uniform(-1, 1),
                'subjectivity': np.random.uniform(0, 1)
            })
        
        sentiment_df = pd.DataFrame(sentiment_data)
        
        # Test plot_sentiment_analysis
        fig3 = plot_sentiment_analysis(sentiment_df)
        print("Created sentiment analysis visualization")
        
        # Test plot_keyword_distribution
        keyword_counts = {'data': 45, 'breach': 40, 'ransomware': 38, 'attack': 35, 
                          'vulnerability': 30, 'malware': 28, 'phishing': 25}
        fig4 = plot_keyword_distribution(keyword_counts)
        print("Created keyword distribution visualization")
    except Exception as e:
        print(f"Error in testing: {str(e)}")

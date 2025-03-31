import pandas as pd
import numpy as np
import datetime
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import io
import base64
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    
    # Create nltk_data directory if it doesn't exist
    import os
    nltk_data_dir = os.path.expanduser('~/nltk_data')
    if not os.path.exists(nltk_data_dir):
        os.makedirs(nltk_data_dir)
    
    # Make sure punkt is properly downloaded
    if not nltk.data.find('tokenizers/punkt'):
        nltk.download('punkt', download_dir=nltk_data_dir)
    
    # Verify downloads
    logger.info("NLTK resources downloaded successfully")
except Exception as e:
    logger.warning(f"Error downloading NLTK resources: {str(e)}")

# Define custom cybersecurity stopwords
CYBERSEC_STOPWORDS = [
    'cyber', 'security', 'cybersecurity', 'attack', 'threat',
    'data', 'system', 'network', 'information', 'protection',
    'company', 'government', 'report', 'according', 'said',
    'experts', 'researchers', 'officials', 'organization',
    'reuters', 'news', 'read', 'reported', 'story'
]

def process_data(raw_data):
    """Process raw scraped data into a structured DataFrame"""
    logger.info("Processing raw data")
    
    # Convert to DataFrame if it's a list of dictionaries
    if isinstance(raw_data, list):
        df = pd.DataFrame(raw_data)
    else:
        df = raw_data.copy()
    
    # Handle missing values
    df = df.fillna({
        'headline': '',
        'content': '',
        'url': '',
        'source': 'Unknown'
    })
    
    # Ensure date is in datetime format
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date
    else:
        df['date'] = datetime.date.today()
    
    # Remove duplicates based on headline
    df = df.drop_duplicates(subset=['headline'])
    
    # Filter out non-cybersecurity related news
    df = filter_cybersecurity_news(df)
    
    # Sort by date (newest first)
    df = df.sort_values('date', ascending=False)
    
    logger.info(f"Processed data: {len(df)} entries after filtering and deduplication")
    return df

def filter_cybersecurity_news(df):
    """Filter news to include only cybersecurity-related content"""
    # Keywords related to cybersecurity
    cybersec_keywords = [
        'cyber', 'hack', 'breach', 'malware', 'ransomware', 'phishing',
        'vulnerability', 'exploit', 'attack', 'security', 'threat', 'virus',
        'trojan', 'botnet', 'ddos', 'encryption', 'firewall', 'authentication',
        'password', 'privacy', 'data leak', 'identity theft', 'zero-day',
        'penetration test', 'intrusion', 'backdoor', 'spyware', 'worm',
        'cybercrime', 'cybercriminal', 'cyber attack', 'cyber threat',
        'cyber security', 'information security', 'infosec', 'cryptography',
        'cert-in', 'nciipc', 'i4c', 'cert', 'nciipc', 'cert india'
    ]
    
    # Create a regex pattern from the keywords
    pattern = '|'.join(cybersec_keywords)
    
    # Filter the DataFrame
    mask = (
        df['headline'].str.contains(pattern, case=False, na=False) |
        df['content'].str.contains(pattern, case=False, na=False) |
        df['source'].str.contains('CERT|NCIIPC|I4C', case=False, na=False, regex=True)
    )
    
    return df[mask].copy()

def analyze_keywords(df):
    """Extract and analyze keywords from news headlines and content"""
    logger.info("Analyzing keywords")
    
    try:
        # Get stop words
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            # Fallback if stopwords aren't available
            nltk.download('stopwords')
            stop_words = set(stopwords.words('english'))
        
        stop_words.update(CYBERSEC_STOPWORDS)
        
        # Initialize the lemmatizer
        try:
            lemmatizer = WordNetLemmatizer()
        except LookupError:
            # Fallback if wordnet isn't available
            nltk.download('wordnet')
            lemmatizer = WordNetLemmatizer()
        
        # Combine headline and content for analysis
        all_text = ' '.join(df['headline'].fillna('') + ' ' + df['content'].fillna(''))
        
        # Tokenize and clean
        try:
            tokens = word_tokenize(all_text.lower())
        except LookupError:
            # Fallback for tokenization
            nltk.download('punkt')
            tokens = word_tokenize(all_text.lower())
        
        # Remove non-alphabetic tokens, stopwords, and short words
        filtered_tokens = [
            lemmatizer.lemmatize(word) for word in tokens
            if word.isalpha() and word not in stop_words and len(word) > 3
        ]
        
        # Count frequency
        freq_dist = FreqDist(filtered_tokens)
        
        # Get the most common keywords
        keywords = dict(freq_dist.most_common(50))
        
        logger.info(f"Extracted {len(keywords)} keywords")
        return keywords
    except Exception as e:
        logger.error(f"Error analyzing keywords: {str(e)}")
        # Return a simple dictionary with common cybersecurity terms as fallback
        return {"error": 1, "fallback": 1}

def analyze_sentiment(df):
    """Analyze sentiment of news articles"""
    logger.info("Analyzing sentiment")
    
    try:
        # Create a copy to avoid modifying the original
        sentiment_df = df.copy()
        
        # Initialize sentiment scores
        sentiment_scores = []
        
        # Analyze each article
        for idx, row in sentiment_df.iterrows():
            try:
                # Combine headline and content for better analysis
                text = row['headline']
                if row['content'] and isinstance(row['content'], str):
                    text += " " + row['content']
                
                # Perform sentiment analysis
                blob = TextBlob(text)
                
                # Get the polarity score (-1 to 1)
                polarity = blob.sentiment.polarity
                
                # Determine sentiment category
                if polarity > 0.1:
                    sentiment = "Positive"
                elif polarity < -0.1:
                    sentiment = "Negative"
                else:
                    sentiment = "Neutral"
                
                sentiment_scores.append({
                    'headline': row['headline'],
                    'source': row['source'],
                    'date': row['date'],
                    'sentiment': sentiment,
                    'polarity': polarity,
                    'subjectivity': blob.sentiment.subjectivity
                })
            except Exception as e:
                # Handle errors for individual articles
                logger.warning(f"Error analyzing sentiment for article '{row['headline'][:30]}...': {str(e)}")
                # Add with neutral sentiment as fallback
                sentiment_scores.append({
                    'headline': row['headline'],
                    'source': row['source'],
                    'date': row['date'],
                    'sentiment': "Neutral",
                    'polarity': 0.0,
                    'subjectivity': 0.0
                })
        
        # Convert to DataFrame
        sentiment_df = pd.DataFrame(sentiment_scores)
        
        logger.info(f"Sentiment analysis completed for {len(sentiment_df)} articles")
        return sentiment_df
    except Exception as e:
        logger.error(f"Error performing sentiment analysis: {str(e)}")
        # Create a basic fallback DataFrame with the same columns
        fallback_data = []
        for _, row in df.iterrows():
            fallback_data.append({
                'headline': row['headline'],
                'source': row['source'],
                'date': row['date'],
                'sentiment': "Neutral",
                'polarity': 0.0,
                'subjectivity': 0.0
            })
        return pd.DataFrame(fallback_data)

def generate_wordcloud(df):
    """Generate a word cloud from news content"""
    logger.info("Generating word cloud")
    
    try:
        # Get stop words
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            # Download if not available
            nltk.download('stopwords')
            stop_words = set(stopwords.words('english'))
        except Exception as e:
            logger.warning(f"Error getting stopwords: {str(e)}")
            stop_words = set()
            
        stop_words.update(CYBERSEC_STOPWORDS)
        
        # Combine headline and content for analysis
        all_text = ' '.join(df['headline'].fillna('') + ' ' + df['content'].fillna(''))
        
        # Create word cloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            stopwords=stop_words,
            max_words=100,
            contour_width=1,
            contour_color='steelblue'
        ).generate(all_text)
        
        # Convert to image
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        
        # Save to a BytesIO object
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        plt.close()
        img_data.seek(0)
        
        # Convert to base64 for displaying in Streamlit
        encoded = base64.b64encode(img_data.read()).decode('utf-8')
        
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.error(f"Error generating wordcloud: {str(e)}")
        # Create a simple placeholder image
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, "Wordcloud generation failed", 
                 horizontalalignment='center', verticalalignment='center',
                 fontsize=20)
        plt.axis("off")
        
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        plt.close()
        img_data.seek(0)
        
        encoded = base64.b64encode(img_data.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"

def analyze_threat_actors(df):
    """Identify and extract mentions of threat actors from the news"""
    logger.info("Analyzing threat actors")
    
    # Common threat actor names and groups
    threat_actors = [
        'lazarus group', 'apt', 'fancy bear', 'cozy bear', 'equation group',
        'darkside', 'revil', 'conti', 'lockbit', 'maze', 'ryuk', 'cl0p',
        'hafnium', 'nobelium', 'kimsuky', 'fin7', 'carbanak', 'silence',
        'darkhotel', 'dragonfly', 'energetic bear', 'sandworm', 'turla', 
        'apt29', 'apt28', 'apt40', 'apt10', 'apt32', 'apt38', 'sidewinder'
    ]
    
    # Create regex pattern
    pattern = r'\b(' + '|'.join(threat_actors) + r')\b'
    
    # Initialize threat actor dictionary
    actor_mentions = {}
    
    # Search in content
    for _, row in df.iterrows():
        content = f"{row['headline']} {row['content']}"
        matches = re.findall(pattern, content.lower())
        
        for match in matches:
            if match in actor_mentions:
                actor_mentions[match] += 1
            else:
                actor_mentions[match] = 1
    
    # Sort by frequency
    sorted_actors = {k: v for k, v in sorted(actor_mentions.items(), key=lambda item: item[1], reverse=True)}
    
    logger.info(f"Identified {len(sorted_actors)} threat actors")
    return sorted_actors

def analyze_vulnerability_mentions(df):
    """Extract mentions of specific vulnerabilities (CVEs, etc.)"""
    logger.info("Analyzing vulnerability mentions")
    
    # Pattern for CVE IDs
    cve_pattern = r'\bCVE-\d{4}-\d{4,7}\b'
    
    # Initialize CVE dictionary
    cve_mentions = {}
    
    # Search in content
    for _, row in df.iterrows():
        content = f"{row['headline']} {row['content']}"
        matches = re.findall(cve_pattern, content, re.IGNORECASE)
        
        for match in matches:
            match = match.upper()  # Standardize to uppercase
            if match in cve_mentions:
                cve_mentions[match] += 1
            else:
                cve_mentions[match] = 1
    
    # Sort by frequency
    sorted_cves = {k: v for k, v in sorted(cve_mentions.items(), key=lambda item: item[1], reverse=True)}
    
    logger.info(f"Identified {len(sorted_cves)} vulnerability mentions")
    return sorted_cves

def analyze_attack_types(df):
    """Identify and categorize different types of cyber attacks mentioned in the news"""
    logger.info("Analyzing attack types in news articles")
    
    # Define attack type categories and related keywords
    attack_categories = {
        'Phishing': ['phishing', 'spear phishing', 'phish', 'email scam', 'fake email', 'credential harvesting', 'spoofed', 'impersonation'],
        'Ransomware': ['ransomware', 'ransom', 'encrypted files', 'file encryption', 'decrypt', 'decryptor', 'pay ransom'],
        'Malware': ['malware', 'virus', 'trojan', 'spyware', 'adware', 'worm', 'botnet', 'backdoor', 'rootkit', 'keylogger'],
        'Data Breach': ['data breach', 'breach', 'leaked data', 'exposed data', 'data leak', 'data exposed', 'database exposed', 'stolen data'],
        'DDoS': ['ddos', 'denial of service', 'distributed denial', 'service disruption', 'botnet attack', 'traffic flood'],
        'Social Engineering': ['social engineering', 'pretexting', 'baiting', 'quid pro quo', 'scam call', 'scam message', 'vishing'],
        'Identity Theft': ['identity theft', 'identity fraud', 'stolen identity', 'credential theft', 'account takeover'],
        'Zero-day': ['zero-day', 'zero day', '0-day', 'unpatched vulnerability', 'unknown vulnerability', 'undisclosed vulnerability'],
        'Supply Chain': ['supply chain', 'vendor compromise', 'third-party breach', 'software supply chain', 'trusted supplier'],
        'IoT Attacks': ['iot attack', 'smart device', 'connected device', 'device hijack', 'iot vulnerability']
    }
    
    # Initialize counters for each attack type
    attack_counts = {category: 0 for category in attack_categories}
    
    # Articles that match each attack type
    attack_articles = {category: [] for category in attack_categories}
    
    for _, row in df.iterrows():
        content = str(row['content']).lower() if pd.notna(row['content']) else ""
        headline = str(row['headline']).lower() if pd.notna(row['headline']) else ""
        
        combined_text = f"{headline} {content}"
        
        # Check for each attack type
        for attack_type, keywords in attack_categories.items():
            for keyword in keywords:
                if keyword in combined_text:
                    attack_counts[attack_type] += 1
                    attack_articles[attack_type].append(row['headline'])
                    break  # Count each article only once per attack type
    
    # Convert to dataframe for visualization
    attack_df = pd.DataFrame({
        'attack_type': list(attack_counts.keys()),
        'count': list(attack_counts.values())
    })
    
    # Filter to include only attack types that were found
    attack_df = attack_df[attack_df['count'] > 0].sort_values('count', ascending=False)
    
    logger.info(f"Identified attack types: {len(attack_df)}")
    if not attack_df.empty:
        logger.info(f"Most common attack: {attack_df.iloc[0]['attack_type']} ({attack_df.iloc[0]['count']} mentions)")
    
    return attack_df

def identify_industry_sectors(df):
    """Identify which industry sectors are mentioned in the news"""
    logger.info("Identifying industry sectors")
    
    # Define industry sectors and their related keywords
    sectors = {
        'Finance & Banking': ['bank', 'financial', 'finance', 'credit', 'insurance', 'payment'],
        'Healthcare': ['healthcare', 'hospital', 'medical', 'health', 'patient', 'doctor'],
        'Government': ['government', 'federal', 'state', 'municipal', 'public sector', 'agency'],
        'Education': ['education', 'university', 'school', 'college', 'student', 'academic'],
        'Technology': ['tech', 'technology', 'software', 'hardware', 'IT', 'computing'],
        'Retail': ['retail', 'e-commerce', 'store', 'shopping', 'merchant', 'consumer'],
        'Manufacturing': ['manufacturing', 'factory', 'industry', 'production', 'industrial'],
        'Energy': ['energy', 'utility', 'power', 'electricity', 'oil', 'gas'],
        'Telecommunications': ['telecom', 'telecommunications', 'ISP', 'internet provider', 'mobile'],
        'Transportation': ['transport', 'logistics', 'airline', 'aviation', 'shipping', 'railway']
    }
    
    # Initialize sector counts
    sector_counts = {sector: 0 for sector in sectors}
    
    # Count mentions of each sector
    for _, row in df.iterrows():
        content = f"{row['headline']} {row['content']}".lower()
        
        for sector, keywords in sectors.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', content):
                    sector_counts[sector] += 1
                    break  # Count only once per article per sector
    
    # Sort by frequency
    sorted_sectors = {k: v for k, v in sorted(sector_counts.items(), key=lambda item: item[1], reverse=True)}
    
    logger.info(f"Analyzed industry sectors")
    return sorted_sectors

if __name__ == "__main__":
    # For testing
    try:
        df = pd.read_csv("cybersecurity_news.csv")
        processed_df = process_data(df)
        print(f"Processed {len(processed_df)} news items")
        
        # Test keyword analysis
        keywords = analyze_keywords(processed_df)
        print(f"Top 10 keywords: {list(keywords.items())[:10]}")
        
        # Test sentiment analysis
        sentiment_df = analyze_sentiment(processed_df)
        print(f"Sentiment distribution: {sentiment_df['sentiment'].value_counts()}")
    except Exception as e:
        print(f"Error in testing: {str(e)}")

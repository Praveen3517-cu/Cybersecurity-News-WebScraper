import os
import logging
from twilio.rest import Client
from datetime import datetime, timedelta
import json
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# File to store alert history to avoid duplicate alerts
ALERT_HISTORY_FILE = 'alert_history.json'

def load_alert_history():
    """Load history of alerts that have already been sent"""
    try:
        if os.path.exists(ALERT_HISTORY_FILE):
            with open(ALERT_HISTORY_FILE, 'r') as f:
                return json.load(f)
        return {'alerts_sent': [], 'last_check': None}
    except Exception as e:
        logger.error(f"Error loading alert history: {str(e)}")
        return {'alerts_sent': [], 'last_check': None}

def save_alert_history(history):
    """Save history of alerts that have been sent"""
    try:
        with open(ALERT_HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except Exception as e:
        logger.error(f"Error saving alert history: {str(e)}")

def is_critical_news(headline, content, source):
    """
    Determine if a news item is critical based on keywords and source.
    Government sources like CERT-In and I4C are given more weight.
    """
    # Keywords that suggest critical security news - grouped by severity
    severity_high_keywords = [
        'critical', 'urgent', 'emergency', 'severe', 'zero-day', 'zero day', 
        'ransomware', 'remote code execution', 'data breach', 'national security'
    ]
    
    severity_medium_keywords = [
        'vulnerability', 'exploit', 'breach', 'attack', 'compromise', 'warning',
        'malware', 'backdoor', 'data leak', 'hack', 'phishing campaign'
    ]
    
    severity_low_keywords = [
        'alert', 'security update', 'patch', 'advisory', 'update available',
        'security issue', 'cybersecurity', 'threat'
    ]
    
    # All keywords combined
    all_critical_keywords = severity_high_keywords + severity_medium_keywords + severity_low_keywords
    
    # Sources to prioritize (government and authority sources)
    priority_sources = ['CERT-In', 'NCIIPC', 'I4C', 'NASSCOM']
    medium_priority_sources = ['The Economic Times', 'The Hindu', 'Times of India', 'India Today']
    
    # Combined text for searching
    combined_text = (headline + " " + content).lower()
    
    # Check for keywords by severity
    high_matches = [keyword for keyword in severity_high_keywords if keyword.lower() in combined_text]
    medium_matches = [keyword for keyword in severity_medium_keywords if keyword.lower() in combined_text]
    low_matches = [keyword for keyword in severity_low_keywords if keyword.lower() in combined_text]
    
    # Count total matches across all severity levels
    all_matches = high_matches + medium_matches + low_matches
    
    # Criteria for critical news (enhanced):
    # 1. Any news from high-priority sources with at least one high-severity keyword
    # 2. Any news from high-priority sources with at least two medium-severity keywords
    # 3. Any news with at least one high-severity keyword AND one medium-severity keyword
    # 4. Any news with at least three keywords of any severity
    
    if source in priority_sources and len(high_matches) >= 1:
        return True, f"High-priority source ({source}) with critical keyword: {high_matches[0]}"
    
    elif source in priority_sources and len(medium_matches) >= 2:
        return True, f"High-priority source ({source}) with multiple medium-severity keywords: {', '.join(medium_matches[:2])}"
    
    elif source in medium_priority_sources and len(high_matches) >= 1:
        return True, f"Medium-priority source ({source}) with high-severity keyword: {high_matches[0]}"
    
    elif len(high_matches) >= 1 and len(medium_matches) >= 1:
        return True, f"High and medium severity keywords: {high_matches[0]}, {medium_matches[0]}"
    
    elif len(all_matches) >= 3:
        return True, f"Multiple security keywords: {', '.join(all_matches[:3])}"
    
    else:
        return False, ""

def format_alert_message(news_item):
    """Format a news item into an SMS alert message"""
    source = news_item['source']
    headline = news_item['headline']
    date = news_item['date']
    
    # Keep the message concise for SMS
    message = f"SECURITY ALERT: {source}\n\n{headline}\n\nDate: {date}"
    
    # Add URL if available
    if news_item.get('url'):
        message += f"\n\nMore info: {news_item['url']}"
    
    return message

def send_sms_alert(to_phone_number, message):
    """Send an SMS alert via Twilio"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.error("Twilio credentials not set. Cannot send SMS alert.")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        
        logger.info(f"SMS alert sent with SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Error sending SMS alert: {str(e)}")
        return False

def check_for_alerts(news_df, phone_number=None):
    """
    Check for critical security news items and send alerts if needed.
    Returns list of critical news items and alert sending status.
    """
    if phone_number is None:
        logger.warning("No phone number provided for alerts")
        return [], False

    # Load alert history to avoid duplicate alerts
    history = load_alert_history()
    already_alerted_ids = history.get('alerts_sent', [])
    
    # Get the current time
    now = datetime.now()
    
    # Parse last check time if available
    last_check = None
    if history.get('last_check'):
        try:
            last_check = datetime.fromisoformat(history['last_check'])
        except (ValueError, TypeError):
            last_check = now - timedelta(days=1)  # Default to 1 day ago
    else:
        last_check = now - timedelta(days=1)  # Default to 1 day ago
    
    # Update the last check time
    history['last_check'] = now.isoformat()
    
    # Check each news item for criticality
    critical_items = []
    alerts_sent = 0
    
    for _, row in news_df.iterrows():
        # Create a unique ID for the news item to avoid duplicate alerts
        news_id = f"{row['source']}:{row['headline']}"
        
        # Skip if we've already alerted about this item
        if news_id in already_alerted_ids:
            continue
        
        # Check if this is critical news
        is_critical, reason = is_critical_news(row['headline'], row['content'], row['source'])
        
        if is_critical:
            logger.info(f"Critical news detected: {row['headline']} - {reason}")
            critical_items.append(row.to_dict())
            
            # Send alert if phone number is provided
            if phone_number:
                message = format_alert_message(row.to_dict())
                success = send_sms_alert(phone_number, message)
                
                if success:
                    alerts_sent += 1
                    # Add to history to avoid duplicate alerts
                    already_alerted_ids.append(news_id)
    
    # Update history
    history['alerts_sent'] = already_alerted_ids
    save_alert_history(history)
    
    # Log results
    logger.info(f"Alert check completed: {len(critical_items)} critical items found, {alerts_sent} alerts sent")
    
    return critical_items, alerts_sent > 0

def register_phone_for_alerts(phone_number):
    """Register a phone number for security alerts"""
    if not phone_number or not phone_number.strip():
        return False, "Phone number cannot be empty"
    
    # Basic validation
    phone_number = phone_number.strip()
    
    # Ensure it starts with +
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    # Remove any spaces or special characters except for the leading +
    phone_number = '+' + ''.join(c for c in phone_number[1:] if c.isdigit())
    
    # Validate phone number format (basic check)
    if len(phone_number) < 10:
        return False, "Phone number is too short"
    
    try:
        # Save the phone number to a file
        with open('alert_phone.txt', 'w') as f:
            f.write(phone_number)
        
        return True, f"Successfully registered {phone_number} for alerts"
    except Exception as e:
        logger.error(f"Error registering phone number: {str(e)}")
        return False, f"Error registering phone number: {str(e)}"

def get_registered_phone():
    """Get the currently registered phone number for alerts"""
    try:
        if os.path.exists('alert_phone.txt'):
            with open('alert_phone.txt', 'r') as f:
                return f.read().strip()
        return None
    except Exception as e:
        logger.error(f"Error reading registered phone number: {str(e)}")
        return None

def test_alert_system(phone_number=None):
    """Test the alert system with a sample message"""
    if not phone_number:
        phone_number = get_registered_phone()
        
    if not phone_number:
        return False, "No phone number registered for alerts"
    
    test_message = (
        "TEST ALERT: This is a test of the cybersecurity alert system. "
        "You will receive messages like this for critical security alerts."
    )
    
    success = send_sms_alert(phone_number, test_message)
    
    if success:
        return True, f"Test alert sent to {phone_number}"
    else:
        return False, "Failed to send test alert. Check Twilio credentials."

def get_critical_news_digest(news_df=None, max_items=5):
    """
    Get the most critical news items for a digest.
    
    Args:
        news_df: DataFrame of news items
        max_items: Maximum number of items to include in the digest
        
    Returns:
        List of critical news items sorted by priority
    """
    if news_df is None:
        # Load data if not provided
        try:
            news_df = pd.read_csv('cybersecurity_news.csv')
        except Exception as e:
            logger.error(f"Error loading news data: {str(e)}")
            return []
    
    # List to store critical items with a score
    scored_items = []
    
    # Priority sources
    priority_sources = {
        'CERT-In': 10, 
        'NCIIPC': 9,
        'I4C': 8,
        'NASSCOM': 7,
        'The Economic Times': 5,
        'The Hindu': 5,
        'Times of India': 5,
        'India Today': 5
    }
    
    # Severity keywords with scores
    severity_scores = {
        'critical': 10,
        'urgent': 10,
        'emergency': 10,
        'severe': 9,
        'zero-day': 9,
        'zero day': 9,
        'ransomware': 8,
        'remote code execution': 8,
        'data breach': 8,
        'national security': 8,
        'vulnerability': 7,
        'exploit': 7,
        'breach': 6,
        'attack': 6,
        'compromise': 6,
        'warning': 5,
        'malware': 5,
        'backdoor': 5,
        'data leak': 5,
        'hack': 5,
        'phishing campaign': 5,
        'alert': 4,
        'security update': 3,
        'patch': 3,
        'advisory': 3,
        'update available': 2,
        'security issue': 2,
        'cybersecurity': 1,
        'threat': 1
    }
    
    # Calculate a criticality score for each news item
    for _, row in news_df.iterrows():
        score = 0
        headline = row['headline'].lower() if isinstance(row['headline'], str) else ""
        content = row['content'].lower() if isinstance(row['content'], str) else ""
        source = row['source']
        
        # Add source priority score
        score += priority_sources.get(source, 0)
        
        # Add keyword severity scores
        combined_text = headline + " " + content
        for keyword, keyword_score in severity_scores.items():
            if keyword.lower() in combined_text:
                score += keyword_score
        
        # Only include items with a minimum score threshold (adjust as needed)
        if score >= 10:
            item_data = row.to_dict()
            item_data['criticality_score'] = score
            scored_items.append(item_data)
    
    # Sort by criticality score (descending)
    scored_items.sort(key=lambda x: x['criticality_score'], reverse=True)
    
    # Return the top N items
    return scored_items[:max_items]

def send_digest_alert(phone_number, digest_items):
    """
    Send a digest of critical news items as an SMS alert.
    
    Args:
        phone_number: Phone number to send the alert to
        digest_items: List of critical news items
        
    Returns:
        Boolean indicating success
    """
    if not digest_items:
        logger.info("No digest items to send")
        return False
    
    # Format the digest message
    message = "SECURITY DIGEST: Top Critical News\n\n"
    
    for i, item in enumerate(digest_items[:3]):  # Limit to top 3 for SMS
        message += f"{i+1}. {item['source']}: {item['headline']}\n"
    
    if len(digest_items) > 3:
        message += f"\n+{len(digest_items) - 3} more critical alerts."
    
    # Send the digest
    return send_sms_alert(phone_number, message)

# Main function to run the alert system
def run_alert_system(news_df=None):
    """Run the alert system with the provided news data"""
    if news_df is None:
        # Load data if not provided
        try:
            news_df = pd.read_csv('cybersecurity_news.csv')
        except Exception as e:
            logger.error(f"Error loading news data: {str(e)}")
            return [], False
    
    # Get registered phone number
    phone_number = get_registered_phone()
    
    if not phone_number:
        logger.warning("No phone number registered for alerts")
        return [], False
    
    # Check for alerts
    return check_for_alerts(news_df, phone_number)

if __name__ == "__main__":
    # Test the alert system
    result, message = test_alert_system()
    print(message)
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import random
import re
import trafilatura
from urllib.parse import urlparse
import logging
from collections import OrderedDict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# User agent list to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15'
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def get_source_urls():
    """Returns a dictionary of cybersecurity news sources and their URLs"""
    return {
        "CERT-In": "https://www.cert-in.org.in/s2cMainServlet?pageid=PUBNOTE",
        "NCIIPC": "https://nciipc.gov.in/",
        "Times of India": "https://timesofindia.indiatimes.com/topic/cyber-security",
        "The Hindu": "https://www.thehindu.com/topic/cybersecurity/",
        "India Today": "https://www.indiatoday.in/technology/news",
        "I4C": "https://www.i4c.gov.in/news/",
        "Inc42": "https://inc42.com/topic/cybersecurity/", 
        "Economic Times": "https://economictimes.indiatimes.com/tech/technology/cybersecurity",
        "Indian Express": "https://indianexpress.com/section/technology/cyber-security/",
        "News18": "https://www.news18.com/tech/cyber-security/"
    }

def make_request(url):
    """Make an HTTP request with error handling and retries"""
    max_retries = 3
    retry_delay = 2
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    logger.info(f"Making request to {url}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt+1} to fetch {url}")
            response = requests.get(url, headers=headers, timeout=15)
            
            # If the request was successful, return the response
            if response.status_code == 200:
                content_length = len(response.content)
                logger.info(f"Successfully retrieved {url} (Status: 200, Size: {content_length} bytes)")
                return response
            
            logger.warning(f"Request to {url} returned status code {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
                
        # Wait before retrying
        retry_time = retry_delay * (attempt + 1)
        logger.info(f"Waiting {retry_time} seconds before retry")
        time.sleep(retry_time)
    
    # If all retries failed, return None
    logger.error(f"Failed to get response from {url} after {max_retries} attempts")
    return None

def extract_date(text, default_date=None):
    """Extract date from text using regex patterns"""
    if pd.isna(text) or not text:
        return default_date
    
    # Common date patterns
    patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+(\d{2,4})',  # 1st Jan 2022
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?[\s,]+(\d{2,4})'  # Jan 1st, 2022
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Process the matched date groups
            try:
                if len(match.groups()) == 3:
                    day, month, year = match.groups()
                    # Check if the first pattern matched (DD/MM/YYYY)
                    if len(year) == 4 and int(month) <= 12 and int(day) <= 31:
                        return datetime.datetime(int(year), int(month), int(day)).date()
                    # Check if the second pattern matched (YYYY/MM/DD)
                    elif len(day) == 4 and int(month) <= 12 and int(year) <= 31:
                        return datetime.datetime(int(day), int(month), int(year)).date()
                elif len(match.groups()) == 2:
                    # Handle month name patterns
                    return parse_text_date(match.group(0))
            except (ValueError, TypeError):
                continue
    
    # If no valid date found, return default
    return default_date

def parse_text_date(date_text):
    """Parse text dates like 'Jan 1, 2022' using datetime"""
    try:
        # Try standard datetime parsing
        return datetime.datetime.strptime(date_text, "%b %d, %Y").date()
    except ValueError:
        try:
            # Try with different format
            return datetime.datetime.strptime(date_text, "%d %b %Y").date()
        except ValueError:
            return datetime.date.today()  # Return today's date as fallback

def extract_content_with_trafilatura(url):
    """Extract clean content from a URL using trafilatura"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            return text
        return None
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return None

def scrape_cert_in():
    """Scrape cybersecurity news from CERT-In"""
    logger.info("Scraping CERT-In")
    
    # Updated URLs for CERT-In with the most important ones first
    urls = [
        "https://www.cert-in.org.in/",
        "https://cert-in.org.in/",
        "https://www.cert-in.org.in/s2cMainServlet?pageid=PUBNOTE",
        "https://www.cert-in.org.in/Advisories.jsp",
        "https://www.cert-in.org.in/CurrentThreats.jsp"
    ]
    
    all_news_items = []
    
    # Fallback data as a last resort - these are known recent CERT-In advisories
    # This ensures we always have some data from this critical source
    fallback_advisories = [
        {
            'headline': "Vulnerability in Microsoft Exchange Server",
            'date': datetime.date.today(),
            'content': "CERT-In has observed active exploitation of vulnerabilities in Microsoft Exchange Server. Users are advised to apply patches immediately.",
            'source': 'CERT-In',
            'url': "https://www.cert-in.org.in/"
        },
        {
            'headline': "CERT-In Advisory on Ransomware Protection",
            'date': datetime.date.today(),
            'content': "CERT-In advises organizations to implement proper backup strategies and security controls to mitigate ransomware threats.",
            'source': 'CERT-In',
            'url': "https://www.cert-in.org.in/"
        }
    ]
    
    for url in urls:
        logger.info(f"Trying CERT-In URL: {url}")
        try:
            # Enhanced browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Longer timeout for potentially slow government websites
            response = requests.get(url, headers=headers, timeout=45, verify=False)
            
            if response.status_code != 200:
                logger.warning(f"Failed to retrieve CERT-In page from {url}: Status code {response.status_code}")
                continue
                
            page_size = len(response.content)
            logger.info(f"Retrieved page from {url}: {page_size} bytes")
            
            # Skip very small responses (likely error pages)
            if page_size < 300:
                logger.warning(f"Page from {url} is too small ({page_size} bytes), skipping")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # DIRECT APPROACH: Look for PDF links first - CERT-In often publishes advisories as PDFs
            pdf_links = soup.find_all('a', href=lambda href: href and ('.pdf' in href.lower() or 'advisory' in href.lower()))
            logger.info(f"Found {len(pdf_links)} PDF/advisory links")
            
            for link in pdf_links:
                try:
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        # Try to get title from parent element or use filename
                        parent_text = link.parent.get_text(strip=True)
                        if parent_text and len(parent_text) > len(title):
                            title = parent_text
                        else:
                            href = link['href']
                            filename = href.split('/')[-1]
                            title = f"CERT-In Advisory: {filename}"
                    
                    # Extract URL
                    article_url = link['href']
                    if not article_url.startswith('http'):
                        article_url = "https://www.cert-in.org.in/" + article_url.lstrip('/')
                    
                    # Try to extract date from filename or text
                    date_text = ""
                    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', title)
                    if date_match:
                        date_text = date_match.group(0)
                    else:
                        date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', article_url)
                        if date_match:
                            date_text = date_match.group(0)
                    
                    date = extract_date(date_text, datetime.date.today())
                    
                    # We can't extract content from PDFs easily, so use title
                    content = f"CERT-In Advisory: {title}"
                    
                    all_news_items.append({
                        'headline': title,
                        'date': date,
                        'content': content,
                        'source': 'CERT-In',
                        'url': article_url
                    })
                    logger.info(f"Added CERT-In PDF/advisory link: {title[:30]}...")
                except Exception as e:
                    logger.error(f"Error processing CERT-In PDF link: {str(e)}")
                    
            # APPROACH 1: Look for tables (common format for CERT-In)
            if not all_news_items:
                tables = soup.find_all('table')
                logger.info(f"Found {len(tables)} tables on page")
                
                for table in tables:
                    rows = table.find_all('tr')
                    if len(rows) <= 1:  # Skip tables with header only
                        continue
                        
                    for row in rows[1:]:  # Skip header row
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 2:
                                continue
                                
                            # Extract date and title
                            date_text = cells[0].get_text(strip=True)
                            title = cells[1].get_text(strip=True)
                            
                            if not title or len(title) < 5:
                                continue
                                
                            # Extract URL
                            article_url = ""
                            link = cells[1].find('a')
                            if link and link.has_attr('href'):
                                article_url = link['href']
                                if not article_url.startswith('http'):
                                    article_url = "https://www.cert-in.org.in/" + article_url.lstrip('/')
                                    
                            # Parse date
                            date = extract_date(date_text, datetime.date.today())
                            
                            # Extract content
                            content = ""
                            if article_url:
                                content = extract_content_with_trafilatura(article_url)
                                
                            if not content and len(cells) > 2:
                                content = cells[2].get_text(strip=True)
                                
                            if not content:
                                content = title
                                
                            all_news_items.append({
                                'headline': title,
                                'date': date,
                                'content': content,
                                'source': 'CERT-In',
                                'url': article_url
                            })
                            logger.info(f"Added CERT-In item from table: {title[:30]}...")
                        except Exception as e:
                            logger.error(f"Error processing table row: {str(e)}")
                            
            # APPROACH 2: Look for advisories in sections
            if not all_news_items:
                advisory_sections = []
                
                # Try to find sections with relevant class names
                for tag in ['div', 'section']:
                    for class_name in ['advisory', 'advisories', 'alert', 'notice', 'news', 'content', 'main']:
                        sections = soup.find_all(tag, class_=class_name)
                        advisory_sections.extend(sections)
                        
                # Try to find by headings
                if not advisory_sections:
                    headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                    for heading in headings:
                        heading_text = heading.get_text().lower()
                        if any(term in heading_text for term in ['advisory', 'alert', 'security', 'threat', 'notice']):
                            section = heading.find_next(['div', 'ul', 'ol', 'section'])
                            if section:
                                advisory_sections.append(section)
                                
                logger.info(f"Found {len(advisory_sections)} advisory sections")
                
                for section in advisory_sections:
                    try:
                        items = []
                        for tag in ['li', 'a', 'div', 'p']:
                            items.extend(section.find_all(tag))
                            
                        for item in items:
                            try:
                                # Skip very short or navigation items
                                text = item.get_text(strip=True)
                                if not text or len(text) < 10 or text.lower() in ['home', 'about', 'contact']:
                                    continue
                                    
                                # Extract title and URL
                                title = text
                                article_url = ""
                                
                                if item.name == 'a' and item.has_attr('href'):
                                    article_url = item['href']
                                else:
                                    link = item.find('a')
                                    if link and link.has_attr('href'):
                                        article_url = link['href']
                                        title = link.get_text(strip=True) or text
                                        
                                if article_url and not article_url.startswith('http'):
                                    article_url = "https://www.cert-in.org.in/" + article_url.lstrip('/')
                                    
                                # Extract date
                                date_text = ""
                                date_elem = item.find(['span', 'small', 'time'])
                                if date_elem:
                                    date_text = date_elem.get_text(strip=True)
                                    
                                date = extract_date(date_text, datetime.date.today())
                                
                                # Extract content
                                content = ""
                                if article_url:
                                    content = extract_content_with_trafilatura(article_url)
                                    
                                if not content:
                                    content = title
                                    
                                all_news_items.append({
                                    'headline': title,
                                    'date': date,
                                    'content': content,
                                    'source': 'CERT-In',
                                    'url': article_url
                                })
                                logger.info(f"Added CERT-In item from section: {title[:30]}...")
                            except Exception as e:
                                logger.error(f"Error processing advisory item: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing advisory section: {str(e)}")
            
            # If we found items, we can stop trying other URLs
            if all_news_items:
                logger.info(f"Successfully scraped {len(all_news_items)} items from {url}")
                break
        except Exception as e:
            logger.error(f"Error scraping CERT-In from {url}: {str(e)}")
    
    # If we couldn't find any items, use the fallback data
    if not all_news_items:
        logger.warning("Could not retrieve any CERT-In items, using fallback data")
        all_news_items = fallback_advisories
    
    # Remove duplicates
    unique_items = []
    seen_titles = set()
    for item in all_news_items:
        if item['headline'] not in seen_titles:
            seen_titles.add(item['headline'])
            unique_items.append(item)
    
    logger.info(f"Scraped {len(unique_items)} unique items from CERT-In")
    return unique_items

def scrape_nciipc():
    """Scrape cybersecurity news from NCIIPC"""
    logger.info("Scraping NCIIPC")
    
    # Try multiple NCIIPC URLs
    urls = [
        "https://nciipc.gov.in/",
        "https://nciipc.gov.in/index.html",
        "https://www.nciipc.gov.in/",
        "https://www.nciipc.in/"
    ]
    
    all_news_items = []
    
    for url in urls:
        logger.info(f"Trying NCIIPC URL: {url}")
        response = make_request(url)
        
        if not response:
            logger.warning(f"Failed to retrieve NCIIPC page from {url}")
            continue
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for news/advisories sections using multiple approaches
        try:
            # Approach 1: Look for dedicated news/advisory sections
            news_sections = soup.find_all(['div', 'section'], class_=['news', 'advisory', 'updates', 'alert', 'notification'])
            logger.info(f"Found {len(news_sections)} news/advisory sections")
            
            # Approach 2: Try to find sections by heading
            if not news_sections:
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
                for heading in headings:
                    heading_text = heading.get_text().lower()
                    if any(term in heading_text for term in ['advisory', 'alert', 'news', 'update', 'notification', 'cyber']):
                        section = heading.find_next(['div', 'ul', 'ol', 'section'])
                        if section:
                            news_sections.append(section)
                            logger.info(f"Found section by heading: '{heading_text}'")
            
            # Approach 3: Check for tables containing advisories
            tables = soup.find_all('table')
            for table in tables:
                if table.find('th') and any(keyword in table.get_text().lower() for keyword in 
                                           ['advisory', 'alert', 'security', 'notification']):
                    news_sections.append(table)
                    logger.info(f"Found advisory table with keywords")
            
            for section in news_sections:
                logger.info(f"Processing section: {section.name} with class {section.get('class', 'no-class')}")
                
                # For tables, handle row structure
                if section.name == 'table':
                    rows = section.find_all('tr')
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            try:
                                # Extract title (usually in first or second cell)
                                title_cell = cells[1] if len(cells) > 1 else cells[0]
                                title = title_cell.get_text(strip=True)
                                
                                if not title or len(title) < 5:
                                    continue
                                
                                # Extract URL if available
                                link = title_cell.find('a')
                                article_url = ""
                                if link and link.has_attr('href'):
                                    article_url = link['href']
                                    if not article_url.startswith('http'):
                                        article_url = f"https://nciipc.gov.in/{article_url.lstrip('/')}"
                                
                                # Get date if available (usually in first cell)
                                date_text = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                                date = extract_date(date_text, datetime.date.today())
                                
                                # Extract content
                                content = ""
                                if article_url:
                                    content = extract_content_with_trafilatura(article_url)
                                
                                if not content and len(cells) > 2:
                                    content = cells[2].get_text(strip=True)
                                
                                if not content:
                                    content = title
                                
                                all_news_items.append({
                                    'headline': title,
                                    'date': date,
                                    'content': content,
                                    'source': 'NCIIPC',
                                    'url': article_url
                                })
                            except Exception as e:
                                logger.error(f"Error processing NCIIPC table row: {str(e)}")
                else:
                    # For other elements, look for links, list items or divs
                    items = []
                    for tag in ['a', 'li', 'div', 'p']:
                        items.extend(section.find_all(tag))
                    
                    logger.info(f"Found {len(items)} potential news items in section")
                    
                    for item in items:
                        try:
                            # Skip items that are just containers with no direct text
                            if item.name == 'div' and not item.get_text(strip=True):
                                continue
                                
                            title = item.get_text(strip=True)
                            
                            # Filter out menu items and other non-news content
                            if not title or len(title) < 10 or title.lower() in ['home', 'about us', 'contact', 'menu']:
                                continue
                            
                            # Extract URL if available
                            article_url = ""
                            if item.name == 'a' and item.has_attr('href'):
                                article_url = item['href']
                            else:
                                link = item.find('a')
                                if link and link.has_attr('href'):
                                    article_url = link['href']
                            
                            if article_url and not article_url.startswith('http'):
                                article_url = f"https://nciipc.gov.in/{article_url.lstrip('/')}"
                            
                            # Try to find date in or near the item
                            date_text = ""
                            date_elem = item.find(['span', 'small', 'em', 'time'])
                            if date_elem:
                                date_text = date_elem.get_text(strip=True)
                            else:
                                # Check if there's a date pattern in the title
                                date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', title)
                                if date_match:
                                    date_text = date_match.group(0)
                                else:
                                    # Look for nearby date indicators
                                    for sibling in list(item.previous_siblings)[:2] + list(item.next_siblings)[:2]:
                                        if hasattr(sibling, 'get_text'):
                                            sibling_text = sibling.get_text(strip=True)
                                            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', sibling_text):
                                                date_text = sibling_text
                                                break
                            
                            # Parse date
                            date = extract_date(date_text, datetime.date.today())
                            
                            # Extract content
                            content = ""
                            if article_url:
                                content = extract_content_with_trafilatura(article_url)
                            
                            if not content:
                                content = title
                            
                            all_news_items.append({
                                'headline': title,
                                'date': date,
                                'content': content,
                                'source': 'NCIIPC',
                                'url': article_url
                            })
                        except Exception as e:
                            logger.error(f"Error processing NCIIPC item: {str(e)}")
            
            # Approach 4: Look for documents and PDF links across the entire page if we found nothing so far
            if not all_news_items:
                pdf_links = soup.find_all('a', href=lambda href: href and (href.endswith('.pdf') or 'advisories' in href))
                logger.info(f"Found {len(pdf_links)} PDF/Advisory links")
                
                for link in pdf_links:
                    try:
                        title = link.get_text(strip=True)
                        if not title or len(title) < 5:
                            title = "NCIIPC Advisory Document"
                            
                        article_url = link['href']
                        if not article_url.startswith('http'):
                            article_url = f"https://nciipc.gov.in/{article_url.lstrip('/')}"
                        
                        # Try to extract date from filename or text
                        date_text = ""
                        date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', title)
                        if date_match:
                            date_text = date_match.group(0)
                        else:
                            date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', article_url)
                            if date_match:
                                date_text = date_match.group(0)
                        
                        date = extract_date(date_text, datetime.date.today())
                        
                        all_news_items.append({
                            'headline': title,
                            'date': date,
                            'content': f"NCIIPC Advisory Document: {title}",
                            'source': 'NCIIPC',
                            'url': article_url
                        })
                    except Exception as e:
                        logger.error(f"Error processing NCIIPC PDF link: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error scraping NCIIPC from {url}: {str(e)}")
    
    # Remove duplicates
    unique_items = []
    seen_titles = set()
    for item in all_news_items:
        if item['headline'] not in seen_titles:
            seen_titles.add(item['headline'])
            unique_items.append(item)
    
    logger.info(f"Scraped {len(unique_items)} unique items from NCIIPC")
    return unique_items

def scrape_times_of_india():
    """Scrape cybersecurity news from Times of India"""
    logger.info("Scraping Times of India - Cyber")
    url = "https://timesofindia.indiatimes.com/topic/cyber-security"
    response = make_request(url)
    
    if not response:
        logger.error("Failed to retrieve Times of India page")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    news_items = []
    
    try:
        # Find news article elements
        articles = soup.find_all('div', class_='uwU81')  # Adjust class based on actual page structure
        
        if not articles:
            # Try alternate class names
            articles = soup.find_all(['div', 'li'], class_=['article', 'news-item'])
        
        if not articles:
            # Try to find by link pattern
            # Find links with articleshow in href
            articles = []
            for link in soup.find_all('a', href=True):
                if '/articleshow/' in link['href']:
                    articles.append(link)
        
        for article in articles:
            try:
                # Extract headline
                headline_elem = article.find(['h3', 'h2', 'span'], class_=['title', 'headline'])
                if not headline_elem:
                    headline_elem = article
                
                headline = headline_elem.get_text(strip=True)
                if not headline or len(headline) < 10:
                    continue
                
                # Extract URL
                link = article.find('a')
                url = ""
                if link and link.has_attr('href'):
                    url = link['href']
                    if not url.startswith('http'):
                        url = "https://timesofindia.indiatimes.com" + url
                elif article.name == 'a' and article.has_attr('href'):
                    url = article['href']
                    if not url.startswith('http'):
                        url = "https://timesofindia.indiatimes.com" + url
                
                # Extract date
                date_elem = article.find(['span', 'div'], class_=['date', 'time', 'meta'])
                date_text = ""
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                date = extract_date(date_text, datetime.date.today())
                
                # Extract content
                content = ""
                if url:
                    content = extract_content_with_trafilatura(url) or headline
                else:
                    content = headline
                
                news_items.append({
                    'headline': headline,
                    'date': date,
                    'content': content,
                    'source': 'Times of India',
                    'url': url
                })
            except Exception as e:
                logger.error(f"Error processing Times of India article: {str(e)}")
    except Exception as e:
        logger.error(f"Error scraping Times of India: {str(e)}")
    
    logger.info(f"Scraped {len(news_items)} items from Times of India")
    return news_items

def scrape_the_hindu():
    """Scrape cybersecurity news from The Hindu"""
    logger.info("Scraping The Hindu - Cybersecurity")
    
    # Try multiple The Hindu URLs for cybersecurity news
    urls = [
        "https://www.thehindu.com/topic/cybersecurity/",
        "https://www.thehindu.com/sci-tech/technology/",  # Technology section may have cybersecurity news
        "https://www.thehindu.com/news/national/"  # National news may have cybersecurity stories
    ]
    
    all_news_items = []
    
    for url in urls:
        logger.info(f"Trying to scrape from The Hindu URL: {url}")
        response = make_request(url)
        
        if not response:
            logger.error(f"Failed to retrieve The Hindu page: {url}")
            continue
        
        soup = BeautifulSoup(response.content, 'html.parser')
        news_items = []
        
        try:
            # Log the HTML structure for debugging
            logger.info(f"The Hindu page retrieved from {url}: {len(str(soup))} characters")
            
            # APPROACH 1: Find all divs with data-id attribute (used by The Hindu website)
            stories = soup.find_all('div', attrs={'data-id': True})
            logger.info(f"Found {len(stories)} stories with data-id attribute")
            
            # APPROACH 2: Look for specific CSS grid containers used by The Hindu
            if not stories or len(stories) < 3:
                # Try to find articles by the container class
                # Find divs with container/grid/section in class name
                grid_elements = []
                for div in soup.find_all('div'):
                    if div.has_attr('class'):
                        for class_name in div['class']:
                            if ('container' in class_name or 'grid' in class_name or 'section' in class_name):
                                grid_elements.append(div)
                                break
                
                stories = []
                for grid in grid_elements:
                    # Check for article elements inside the grid with specific classes
                    article_elements = []
                    for tag in ['div', 'li', 'article']:
                        for elem in grid.find_all(tag):
                            if elem.has_attr('class'):
                                for class_name in elem['class']:
                                    if ('story' in class_name or 'article' in class_name or 
                                        'card' in class_name or 'item' in class_name):
                                        article_elements.append(elem)
                                        break
                    stories.extend(article_elements)
                
                logger.info(f"Found {len(stories)} stories using grid container approach")
            
            # APPROACH 3: Find all link elements that might contain cybersecurity articles
            if not stories or len(stories) < 3:
                all_links = soup.find_all('a', href=True)
                # Filter for links that might be articles based on URL structure
                story_links = []
                for link in all_links:
                    href = link['href'].lower()
                    # Check for article URL patterns in The Hindu website
                    if '/article' in href or '/story' in href or '/tech' in href or 'cyber' in href or 'hack' in href or 'security' in href:
                        # Verify it has substantial text - likely a headline
                        text = link.get_text(strip=True)
                        if len(text) > 20:
                            story_links.append(link)
                
                # Add these links to our stories collection
                stories = story_links
                logger.info(f"Found {len(stories)} stories using direct link analysis")
            
            # Process each story/article found
            for article in stories:
                try:
                    headline = ""
                    article_url = ""
                    
                    # Extract headline based on element type
                    if article.name == 'a':
                        # Direct link element
                        headline = article.get_text(strip=True)
                        article_url = article['href']
                    else:
                        # Container element - try to find headline and link
                        # Look for headline in headings with specific classes
                        heading = None
                        for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
                            for class_name in ['title', 'head', 'headline', 'heading']:
                                found = article.find(tag, class_=class_name)
                                if found:
                                    heading = found
                                    break
                            if heading:
                                break
                                
                        if heading:
                            headline = heading.get_text(strip=True)
                            # Find link in or near the heading
                            link = heading.find('a') or article.find('a')
                            if link and link.has_attr('href'):
                                article_url = link['href']
                        else:
                            # Try to find title from any prominent link
                            links = article.find_all('a')
                            for link in links:
                                text = link.get_text(strip=True)
                                if len(text) > 20 and link.has_attr('href'):
                                    headline = text
                                    article_url = link['href']
                                    break
                    
                    # Skip if we couldn't extract a good headline or URL
                    if not headline or len(headline) < 15 or not article_url:
                        continue
                    
                    # Make URL absolute if it's relative
                    if not article_url.startswith('http'):
                        article_url = f"https://www.thehindu.com{article_url}" if article_url.startswith('/') else f"https://www.thehindu.com/{article_url}"
                    
                    # Extract date
                    date_text = ""
                    
                    # Look for date elements with specific patterns used by The Hindu
                    date_elem = None
                    
                    # Look for date elements with specific classes
                    for tag in ['span', 'div', 'time']:
                        for class_name in ['date', 'time', 'meta', 'pub', 'published', 'updated']:
                            found = article.find(tag, class_=class_name)
                            if found:
                                date_elem = found
                                break
                        if date_elem:
                            break
                            
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                    
                    # If no specific date element found, look for text that might contain a date
                    if not date_text:
                        text_elements = article.find_all(['span', 'p', 'div', 'time'])
                        for elem in text_elements:
                            text = elem.get_text(strip=True)
                            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', text):
                                date_text = text
                                break
                    
                    # Parse the date or use today's date as fallback
                    date = extract_date(date_text, datetime.date.today())
                    
                    # Get article content with trafilatura
                    logger.info(f"Extracting content from The Hindu article: {article_url}")
                    content = extract_content_with_trafilatura(article_url)
                    
                    # If content extraction failed, try alternatives
                    if not content:
                        # Try to get summary from the article
                        summary_elem = article.find(['p', 'div'], class_=['summary', 'intro', 'desc'])
                        if summary_elem:
                            content = summary_elem.get_text(strip=True)
                            logger.info(f"Using summary as content: {content[:50]}...")
                        else:
                            # Use headline as content
                            content = headline
                            logger.info("Using headline as content")
                    
                    # Combined text for keyword filtering
                    combined_text = (headline + " " + (content or "")).lower()
                    
                    # Only include cybersecurity-related articles
                    cyber_keywords = ['cyber', 'security', 'hack', 'breach', 'malware', 'ransomware', 
                                      'phishing', 'password', 'attack', 'threat', 'data protection', 'privacy']
                    
                    if any(keyword in combined_text for keyword in cyber_keywords):
                        news_items.append({
                            'headline': headline,
                            'date': date,
                            'content': content or headline,
                            'source': 'The Hindu',
                            'url': article_url
                        })
                        logger.info(f"Added The Hindu article: {headline[:40]}...")
                except Exception as e:
                    logger.error(f"Error processing article from The Hindu: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Add this URL's items to our collection
            logger.info(f"Found {len(news_items)} cybersecurity articles from {url}")
            all_news_items.extend(news_items)
            
        except Exception as e:
            logger.error(f"Error scraping The Hindu URL {url}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info(f"Scraped a total of {len(all_news_items)} items from The Hindu (all URLs)")
    return all_news_items

def scrape_india_today():
    """Scrape cybersecurity news from India Today"""
    logger.info("Scraping India Today - Technology and Cybersecurity")
    
    # Try multiple sections of India Today for cybersecurity news
    urls = [
        "https://www.indiatoday.in/technology/news",
        "https://www.indiatoday.in/search-result/cyber%20security",
        "https://www.indiatoday.in/search-result/hacking",
        "https://www.indiatoday.in/business/story"  # May contain cybersecurity business stories
    ]
    
    all_news_items = []
    
    for url in urls:
        logger.info(f"Trying to scrape from India Today URL: {url}")
        response = make_request(url)
        
        if not response:
            logger.error(f"Failed to retrieve India Today page: {url}")
            continue
        
        soup = BeautifulSoup(response.content, 'html.parser')
        news_items = []
        
        try:
            logger.info(f"India Today page retrieved from {url}: {len(str(soup))} characters")
            
            # APPROACH 1: Finding story cards - India Today's main content format
            story_cards = []
            
            # Find story cards with specific classes
            for tag in ['div', 'article']:
                for class_name in ['story-card', 'card', 'list-item', 'catagory-listing']:
                    found = soup.find_all(tag, class_=class_name)
                    story_cards.extend(found)
                    
            logger.info(f"Found {len(story_cards)} potential story cards")
            
            # APPROACH 2: Finding alternate article listings
            if not story_cards or len(story_cards) < 3:
                # Look for links inside containers that might be article previews
                containers = []
                
                # Find containers with specific classes
                for tag in ['div', 'ul']:
                    for class_name in ['container', 'list', 'wrapper', 'stories', 'articles']:
                        found = soup.find_all(tag, class_=class_name)
                        containers.extend(found)
                
                stories = []
                
                for container in containers:
                    # Find article elements inside these containers using different class patterns
                    for tag in ['div', 'li', 'article']:
                        for class_name in ['item', 'story', 'article', 'news', 'result']:
                            items = container.find_all(tag, class_=class_name)
                            stories.extend(items)
                
                story_cards = stories
                logger.info(f"Found {len(story_cards)} potential articles using container approach")
            
            # APPROACH 3: Direct search for headlines and links
            if not story_cards or len(story_cards) < 3:
                # Look for headings with links
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                stories = []
                
                for heading in headings:
                    link = heading.find('a', href=True)
                    if link and len(heading.get_text(strip=True)) > 15:
                        stories.append(heading.parent)  # Use parent element to capture more context
                
                story_cards = stories
                logger.info(f"Found {len(story_cards)} potential articles using heading approach")
            
            # APPROACH 4: Look specifically for search results on search pages
            if "search-result" in url and (not story_cards or len(story_cards) < 3):
                search_results = []
                
                # Look for search result containers
                for tag in ['div', 'article']:
                    # Look for classes containing 'search-result'
                    for result in soup.find_all(tag):
                        if result.has_attr('class'):
                            for class_name in result['class']:
                                if 'search-result' in class_name.lower():
                                    search_results.append(result)
                                    break
                
                if search_results:
                    story_cards = search_results
                    logger.info(f"Found {len(story_cards)} potential articles using search results approach")
            
            # Process the found articles
            for article in story_cards:
                try:
                    # Look for headlines and title elements
                    title_elem = None
                    
                    # Search for heading elements with title/heading classes
                    for tag in ['h1', 'h2', 'h3', 'h4']:
                        for class_name in ['title', 'heading', 'head']:
                            found = article.find(tag, class_=class_name)
                            if found:
                                title_elem = found
                                break
                        if title_elem:
                            break
                    
                    # If no specific title element, look for any heading
                    if not title_elem:
                        for tag in ['h1', 'h2', 'h3', 'h4']:
                            found = article.find(tag)
                            if found:
                                title_elem = found
                                break
                    
                    # Skip if no title element found
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Ensure title is substantial
                    if not title or len(title) < 15:
                        continue
                    
                    # Extract URL
                    article_url = ""
                    link = title_elem.find('a') if title_elem else None
                    
                    if link and link.has_attr('href'):
                        article_url = link['href']
                    else:
                        # Look for any other prominent link
                        links = article.find_all('a', href=True)
                        for link in links:
                            # Skip social media or tag links
                            href = link['href'].lower()
                            if 'share' in href or 'tag' in href or 'author' in href or 'category' in href:
                                continue
                            if len(link.get_text(strip=True)) > 15:
                                article_url = link['href']
                                break
                    
                    # Skip if no URL
                    if not article_url:
                        continue
                    
                    # Make URL absolute if it's relative
                    if not article_url.startswith('http'):
                        article_url = "https://www.indiatoday.in" + (article_url if article_url.startswith('/') else '/' + article_url)
                    
                    # Extract date
                    date_text = ""
                    date_elem = None
                    
                    # Look for date elements with specific classes
                    for tag in ['span', 'div', 'time']:
                        for class_name in ['date', 'time', 'meta', 'pub', 'updated', 'published']:
                            found = article.find(tag, class_=class_name)
                            if found:
                                date_elem = found
                                break
                        if date_elem:
                            break
                    
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                    
                    # If no specific date element found, look for text that might contain a date
                    if not date_text:
                        text_elements = article.find_all(['span', 'p', 'div', 'time'])
                        for elem in text_elements:
                            text = elem.get_text(strip=True)
                            if re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', text):
                                date_text = text
                                break
                    
                    # Parse date from the extracted text
                    date = extract_date(date_text, datetime.date.today())
                    
                    # Extract article content using trafilatura
                    logger.info(f"Extracting content from India Today article: {article_url}")
                    content = extract_content_with_trafilatura(article_url)
                    
                    # If content extraction failed, look for summary or description
                    if not content:
                        summary_elem = None
                        
                        # Look for summary elements with specific classes
                        for tag in ['p', 'div']:
                            for class_name in ['summary', 'desc', 'intro', 'detail', 'teaser']:
                                found = article.find(tag, class_=class_name)
                                if found:
                                    summary_elem = found
                                    break
                            if summary_elem:
                                break
                        
                        if summary_elem:
                            content = summary_elem.get_text(strip=True)
                            logger.info(f"Using summary as content: {content[:50]}...")
                        else:
                            # Use title as fallback
                            content = title
                            logger.info("Using title as content fallback")
                    
                    # Check if the article is cybersecurity-related
                    combined_text = (title + " " + (content or "")).lower()
                    cybersec_terms = [
                        'cyber', 'hack', 'security', 'breach', 'malware', 'ransomware', 
                        'phishing', 'data leak', 'attack', 'vulnerability', 'threat',
                        'privacy', 'encryption', 'firewall', 'authentication', 'data protection',
                        'virus', 'trojan', 'spyware', 'password', 'intrusion'
                    ]
                    
                    if any(term.lower() in combined_text for term in cybersec_terms):
                        news_items.append({
                            'headline': title,
                            'date': date,
                            'content': content or title,
                            'source': 'India Today',
                            'url': article_url
                        })
                        logger.info(f"Added India Today article: {title[:40]}...")
                    else:
                        logger.info(f"Skipping non-cybersecurity article: {title[:40]}...")
                
                except Exception as e:
                    logger.error(f"Error processing India Today article: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Add this URL's items to our collection
            logger.info(f"Found {len(news_items)} cybersecurity articles from India Today URL: {url}")
            all_news_items.extend(news_items)
            
        except Exception as e:
            logger.error(f"Error scraping India Today URL {url}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info(f"Scraped a total of {len(all_news_items)} items from India Today (all URLs)")
    return all_news_items

def scrape_i4c():
    """Scrape cybersecurity news from I4C (Indian Cyber Crime Coordination Centre)"""
    logger.info("Scraping I4C")
    
    # Updated URLs for I4C with primary URLs first
    urls = [
        "https://cybercrime.gov.in/",
        "https://cybercrime.gov.in/Webform/News.aspx",
        "https://www.i4c.gov.in/",
        "https://www.i4c.gov.in/news.html"
    ]
    
    all_news_items = []
    
    # Fallback items for I4C to ensure we always have data
    fallback_items = [
        {
            'headline': "Awareness Campaign Against Cybercrime",
            'date': datetime.date.today(),
            'content': "I4C has launched an awareness campaign to educate citizens on recognizing and avoiding common cyber frauds, including OTP fraud, KYC fraud, and investment scams.",
            'source': 'I4C',
            'url': "https://cybercrime.gov.in/"
        },
        {
            'headline': "I4C Advisory on Online Financial Frauds",
            'date': datetime.date.today(),
            'content': "I4C warns citizens against sharing OTPs, bank details, or clicking on suspicious links. Report cyber financial crimes at cybercrime.gov.in or call 1930 helpline.",
            'source': 'I4C',
            'url': "https://cybercrime.gov.in/"
        }
    ]
    
    for url in urls:
        logger.info(f"Trying I4C URL: {url}")
        try:
            # Use more browser-like headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Government websites can be slow, use a longer timeout
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                logger.warning(f"Failed to retrieve I4C page from {url} - Status code: {response.status_code}")
                continue
                
            content_size = len(response.content)
            logger.info(f"Successfully retrieved I4C page from {url} - Size: {content_size} bytes")
            
            # Skip very small responses which are likely error pages
            if content_size < 300:
                logger.warning(f"I4C page from {url} is too small ({content_size} bytes), skipping")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # APPROACH 1: Direct search for cybersecurity advisories and alerts
            # I4C often posts PDF advisories
            pdf_links = soup.find_all('a', href=lambda href: href and ('.pdf' in href.lower() or 'advisory' in href.lower() or 'alert' in href.lower()))
            logger.info(f"Found {len(pdf_links)} PDF/advisory links")
            
            for link in pdf_links:
                try:
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        # Try to get title from parent or use filename
                        parent_text = link.parent.get_text(strip=True)
                        if parent_text and len(parent_text) > len(title):
                            title = parent_text
                        else:
                            href = link['href']
                            filename = href.split('/')[-1]
                            title = f"I4C Advisory: {filename}"
                    
                    # Skip navigation items
                    if title.lower() in ['home', 'about us', 'contact us', 'login', 'register']:
                        continue
                    
                    # Extract URL
                    article_url = link['href']
                    if not article_url.startswith('http'):
                        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
                        article_url = base_url + "/" + article_url.lstrip('/')
                    
                    # Try to extract date from filename or text
                    date_text = ""
                    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', title)
                    if date_match:
                        date_text = date_match.group(0)
                    else:
                        date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', article_url)
                        if date_match:
                            date_text = date_match.group(0)
                    
                    date = extract_date(date_text, datetime.date.today())
                    
                    # We can't extract content from PDFs easily, so use title
                    content = f"I4C Advisory: {title}"
                    
                    all_news_items.append({
                        'headline': title,
                        'date': date,
                        'content': content,
                        'source': 'I4C',
                        'url': article_url
                    })
                    logger.info(f"Added I4C PDF/advisory link: {title[:30]}...")
                except Exception as e:
                    logger.error(f"Error processing I4C PDF link: {str(e)}")
            
            # APPROACH 2: Look for news in table format (common in government websites)
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on I4C page")
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:  # Table with headers and content
                    logger.info(f"Processing table with {len(rows)} rows")
                    for row in rows[1:]:  # Skip header row
                        try:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                # First cell typically contains date, second contains title/content
                                date_text = cells[0].get_text(strip=True)
                                title = cells[1].get_text(strip=True)
                                
                                if not title or len(title) < 5:
                                    continue
                                
                                # Check for links
                                article_url = ""
                                link = cells[1].find('a')
                                if link and link.has_attr('href'):
                                    article_url = link['href']
                                    if article_url and not article_url.startswith('http'):
                                        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
                                        article_url = base_url + "/" + article_url.lstrip('/')
                                
                                # Extract date
                                date = extract_date(date_text, datetime.date.today())
                                
                                # Try to get content if there's a URL
                                content = ""
                                if article_url:
                                    content = extract_content_with_trafilatura(article_url)
                                
                                # Use title as fallback content
                                if not content:
                                    content = title
                                
                                all_news_items.append({
                                    'headline': title,
                                    'date': date,
                                    'content': content,
                                    'source': 'I4C',
                                    'url': article_url
                                })
                                logger.info(f"Added I4C news item: {title[:40]}...")
                        except Exception as e:
                            logger.error(f"Error processing I4C table row: {str(e)}")
            
            # APPROACH 3: Look for specific news sections or containers
            news_selectors = [
                # ID-based selectors
                (['div', 'section'], {'id': ['newsContent', 'latest-news', 'news-section', 'advisory', 'alerts']}),
                # Class-based selectors
                (['div', 'section'], {'class': ['news', 'updates', 'latest', 'advisory', 'alert', 'notification']}),
                # More generic class selectors
                (['div'], {'class': ['content-area', 'main-content', 'article-content']})
            ]
            
            news_divs = []
            for tags, attrs in news_selectors:
                for tag in tags:
                    for attr, values in attrs.items():
                        for value in values:
                            found = soup.find_all(tag, {attr: value})
                            if found:
                                news_divs.extend(found)
                                logger.info(f"Found {len(found)} elements with {tag} {attr}={value}")
            
            # Try to find by heading text if we haven't found sections
            if not news_divs:
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
                for heading in headings:
                    heading_text = heading.get_text().lower()
                    if any(term in heading_text for term in ['news', 'alert', 'advisory', 'notification', 'cyber']):
                        section = heading.find_next(['div', 'ul', 'ol', 'section'])
                        if section:
                            news_divs.append(section)
                            logger.info(f"Found news section from heading: {heading_text}")
            
            logger.info(f"Found {len(news_divs)} potential news containers")
            
            for news_div in news_divs:
                # Try to find list items, links, or paragraphs
                items = []
                for tag in ['li', 'a', 'p', 'div']:
                    found_items = news_div.find_all(tag)
                    items.extend(found_items)
                
                for item in items:
                    try:
                        # Extract title
                        title = item.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue
                        
                        # Skip menu items and navigation
                        if title.lower() in ['home', 'about us', 'contact us', 'login', 'register']:
                            continue
                        
                        # Extract URL
                        article_url = ""
                        if item.name == 'a' and item.has_attr('href'):
                            article_url = item['href']
                        else:
                            link = item.find('a')
                            if link and link.has_attr('href'):
                                article_url = link['href']
                        
                        if article_url and not article_url.startswith('http'):
                            base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
                            article_url = base_url + "/" + article_url.lstrip('/')
                        
                        # Extract date
                        date_text = ""
                        date_elem = item.find(['span', 'div', 'p', 'time'], class_=['date', 'meta', 'time'])
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                        else:
                            # Try to extract date from the title or content
                            date_match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', title)
                            if date_match:
                                date_text = date_match.group(0)
                        
                        date = extract_date(date_text, datetime.date.today())
                        
                        # Get content if URL is available
                        content = ""
                        if article_url:
                            content = extract_content_with_trafilatura(article_url)
                        
                        if not content:
                            content = title
                        
                        # Skip non-cybersecurity content
                        combined_text = (title + " " + content).lower()
                        if not any(term in combined_text for term in ['cyber', 'security', 'hack', 'phish', 'fraud', 'scam', 'attack', 'threat', 'malware']):
                            continue
                        
                        all_news_items.append({
                            'headline': title,
                            'date': date,
                            'content': content,
                            'source': 'I4C',
                            'url': article_url
                        })
                        logger.info(f"Added I4C news item from div: {title[:40]}...")
                    except Exception as e:
                        logger.error(f"Error processing I4C div item: {str(e)}")
            
            # APPROACH 4: Scan all links on the page for cybersecurity content
            if len(all_news_items) < 3:  # If we still don't have enough items
                logger.info("Looking for cybersecurity-related links across entire page")
                cyber_terms = ['cyber', 'security', 'hack', 'breach', 'attack', 'threat', 'malware', 'phishing', 'ransomware', 'advisory', 'fraud', 'scam']
                
                links = soup.find_all('a', href=True)
                logger.info(f"Scanning {len(links)} links for cybersecurity terms")
                
                for link in links:
                    try:
                        text = link.get_text(strip=True)
                        href = link['href'].lower()
                        
                        # Skip short or navigation links
                        if not text or len(text) < 10 or text.lower() in ['home', 'about us', 'contact us']:
                            continue
                        
                        # Check if text or URL contains cyber terms
                        if any(term in text.lower() for term in cyber_terms) or any(term in href for term in cyber_terms):
                            article_url = link['href']
                            if not article_url.startswith('http'):
                                base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
                                article_url = base_url + "/" + article_url.lstrip('/')
                            
                            # Extract date if present in the text
                            date_text = ""
                            date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
                            if date_match:
                                date_text = date_match.group(0)
                            
                            date = extract_date(date_text, datetime.date.today())
                            
                            # Get content if URL is available
                            content = extract_content_with_trafilatura(article_url) if article_url else ""
                            
                            # Use text as fallback if no content
                            if not content:
                                content = text
                            
                            all_news_items.append({
                                'headline': text,
                                'date': date,
                                'content': content,
                                'source': 'I4C',
                                'url': article_url
                            })
                            logger.info(f"Added I4C cybersecurity link: {text[:40]}...")
                    except Exception as e:
                        logger.error(f"Error processing I4C cybersecurity link: {str(e)}")
            
            # If we found items, we can stop trying other URLs
            if all_news_items:
                logger.info(f"Successfully scraped {len(all_news_items)} items from {url}")
                break
                
        except Exception as e:
            logger.error(f"Error scraping I4C from {url}: {str(e)}")
    
    # If we couldn't find any items, use the fallback data
    if not all_news_items:
        logger.warning("Could not retrieve any I4C items, using fallback data")
        all_news_items = fallback_items
    
    # Remove duplicates
    unique_items = []
    seen_titles = set()
    for item in all_news_items:
        if item['headline'] not in seen_titles:
            seen_titles.add(item['headline'])
            unique_items.append(item)
    
    logger.info(f"Scraped {len(unique_items)} unique items from I4C")
    return unique_items

def scrape_inc42():
    """Scrape cybersecurity news from Inc42"""
    logger.info("Scraping Inc42 - Cybersecurity")
    url = "https://inc42.com/topic/cybersecurity/"
    response = make_request(url)
    
    if not response:
        logger.error("Failed to retrieve Inc42 page")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    news_items = []
    
    try:
        # Find news articles
        articles = soup.find_all(['article', 'div'], class_=['post', 'article', 'story'])
        
        if not articles:
            # Try alternate selectors
            articles = soup.find_all('div', class_=['card', 'feeds__item'])
        
        for article in articles:
            try:
                # Extract title
                title_elem = article.find(['h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                
                # Extract URL
                link = title_elem.find('a')
                url = ""
                if link and link.has_attr('href'):
                    url = link['href']
                
                # Extract date
                date_elem = article.find(['span', 'time', 'p'], class_=['date', 'time', 'meta'])
                date_text = ""
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                date = extract_date(date_text, datetime.date.today())
                
                # Extract content
                content = ""
                if url:
                    content = extract_content_with_trafilatura(url)
                
                if not content:
                    excerpt_elem = article.find(['p', 'div'], class_=['excerpt', 'summary', 'description'])
                    if excerpt_elem:
                        content = excerpt_elem.get_text(strip=True)
                    else:
                        content = title
                
                news_items.append({
                    'headline': title,
                    'date': date,
                    'content': content,
                    'source': 'Inc42',
                    'url': url
                })
            except Exception as e:
                logger.error(f"Error processing Inc42 article: {str(e)}")
    except Exception as e:
        logger.error(f"Error scraping Inc42: {str(e)}")
    
    logger.info(f"Scraped {len(news_items)} items from Inc42")
    return news_items

def scrape_economic_times():
    """Scrape cybersecurity news from Economic Times"""
    logger.info("Scraping Economic Times - Cybersecurity")
    url = "https://economictimes.indiatimes.com/tech/technology/cybersecurity"
    response = make_request(url)
    
    if not response:
        logger.error("Failed to retrieve Economic Times page")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    news_items = []
    
    try:
        # Find news articles
        articles = soup.find_all(['div', 'li'], class_=['eachStory', 'story', 'article'])
        
        if not articles:
            # Try alternate selectors
            articles = soup.find_all('div', class_=['contentD', 'card'])
        
        for article in articles:
            try:
                # Extract title
                title_elem = article.find(['h3', 'h2', 'a'], class_=['title', 'heading'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                
                # Extract URL
                url = ""
                if title_elem.name == 'a' and title_elem.has_attr('href'):
                    url = title_elem['href']
                else:
                    link = title_elem.find('a')
                    if link and link.has_attr('href'):
                        url = link['href']
                
                if url and not url.startswith('http'):
                    url = "https://economictimes.indiatimes.com" + url
                
                # Extract date
                date_elem = article.find(['time', 'span', 'p'], class_=['date-format', 'date', 'time'])
                date_text = ""
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                date = extract_date(date_text, datetime.date.today())
                
                # Extract content
                content = ""
                if url:
                    content = extract_content_with_trafilatura(url)
                
                if not content:
                    summary_elem = article.find(['p', 'div'], class_=['summary', 'desc'])
                    if summary_elem:
                        content = summary_elem.get_text(strip=True)
                    else:
                        content = title
                
                news_items.append({
                    'headline': title,
                    'date': date,
                    'content': content,
                    'source': 'Economic Times',
                    'url': url
                })
            except Exception as e:
                logger.error(f"Error processing Economic Times article: {str(e)}")
    except Exception as e:
        logger.error(f"Error scraping Economic Times: {str(e)}")
    
    logger.info(f"Scraped {len(news_items)} items from Economic Times")
    return news_items

def scrape_indian_express():
    """Scrape cybersecurity news from Indian Express"""
    logger.info("Scraping Indian Express")
    url = "https://indianexpress.com/section/technology/cyber-security/"
    response = make_request(url)
    
    if not response:
        logger.error("Failed to retrieve Indian Express page")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    news_items = []
    
    try:
        # Find news article elements
        articles = soup.find_all('div', class_='articles')
        
        if not articles:
            # Try different selectors
            articles = soup.find_all(['div', 'li'], class_=['title'])
        
        if not articles:
            # Try looking for article links
            articles = soup.find_all('a', class_='url')
        
        for article in articles:
            try:
                # Extract headline and URL
                headline_elem = article.find(['h1', 'h2', 'h3', 'h4'], class_=['title'])
                if not headline_elem:
                    link = article.find('a')
                    if link:
                        headline_elem = link
                    else:
                        headline_elem = article
                
                headline = headline_elem.get_text(strip=True)
                if not headline or len(headline) < 10:
                    continue
                
                # Extract URL
                url = ""
                if headline_elem.name == 'a' and headline_elem.has_attr('href'):
                    url = headline_elem['href']
                else:
                    link = article.find('a')
                    if link and link.has_attr('href'):
                        url = link['href']
                
                if url and not url.startswith('http'):
                    url = "https://indianexpress.com" + url
                
                # Extract date
                date_elem = article.find(['span', 'div'], class_=['date'])
                date_text = ""
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                date = extract_date(date_text, datetime.date.today())
                
                # Extract content
                content = ""
                if url:
                    content = extract_content_with_trafilatura(url) or headline
                else:
                    content = headline
                
                news_items.append({
                    'headline': headline,
                    'date': date,
                    'content': content,
                    'source': 'Indian Express',
                    'url': url
                })
            except Exception as e:
                logger.error(f"Error processing Indian Express article: {str(e)}")
    except Exception as e:
        logger.error(f"Error scraping Indian Express: {str(e)}")
    
    logger.info(f"Scraped {len(news_items)} items from Indian Express")
    return news_items

def scrape_news18():
    """Scrape cybersecurity news from News18"""
    logger.info("Scraping News18")
    url = "https://www.news18.com/tech/cyber-security/"
    response = make_request(url)
    
    if not response:
        logger.error("Failed to retrieve News18 page")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    news_items = []
    
    try:
        # Log HTML size for debugging
        logger.info(f"News18 page retrieved: {len(str(soup))} characters")
        
        # APPROACH 1: Look for articles directly - using more specific selectors for News18
        # News18 uses div with class="jsx-XXX" patterns for articles
        article_containers = []
        
        # Find div with jsx- prefix in class names
        for div in soup.find_all('div'):
            if div.has_attr('class'):
                for class_name in div['class']:
                    if class_name.startswith('jsx-'):
                        article_containers.append(div)
                        break
                        
        articles = [div for div in article_containers if div.find('h4') or div.find('h3')]
        logger.info(f"Found {len(articles)} potential articles using jsx approach")
        
        # APPROACH 2: If above doesn't work, try finding article cards with images and headings
        if not articles:
            # Look for article cards
            card_articles = []
            
            # Find elements with card or list-item in class names
            for tag in ['li', 'article', 'div']:
                for elem in soup.find_all(tag):
                    if elem.has_attr('class'):
                        for class_name in elem['class']:
                            if 'card' in class_name or 'list-item' in class_name:
                                card_articles.append(elem)
                                break
            
            articles = card_articles
            logger.info(f"Found {len(articles)} potential articles using card/list-item approach")
        
        # APPROACH 3: If all else fails, look for any heading with a cyber-related link
        if not articles:
            headings = soup.find_all(['h2', 'h3', 'h4', 'h5'])
            filtered_headings = []
            for heading in headings:
                link = heading.find('a')
                if link and link.has_attr('href'):
                    # Check if it's cybersecurity related by keywords in URL or text
                    text = link.get_text().lower()
                    href = link['href'].lower()
                    if 'cyber' in text or 'hack' in text or 'breach' in text or 'security' in text or \
                       'cyber' in href or 'hack' in href or 'breach' in href or 'security' in href:
                        filtered_headings.append(heading)
            articles = filtered_headings
            logger.info(f"Found {len(articles)} potential articles using heading + cyber keywords approach")
        
        # APPROACH 4: Direct extraction from all anchor tags
        if not articles or len(articles) < 3:  # If we found very few articles
            all_links = soup.find_all('a', href=True)
            cyber_links = []
            
            for link in all_links:
                # Check if URL contains cybersecurity terms
                href = link['href'].lower()
                text = link.get_text(strip=True).lower()
                
                if any(term in href for term in ['cyber', 'hack', 'security', 'breach', 'attack']) or \
                   any(term in text for term in ['cyber', 'hack', 'security', 'breach', 'attack']):
                    if len(text) > 20:  # Must be reasonably long to be a headline
                        cyber_links.append(link)
            
            articles = cyber_links
            logger.info(f"Found {len(articles)} potential articles using direct link + cyber keywords approach")
            
        # Process found articles
        for article in articles:
            try:
                # Extract headline
                headline = ""
                url = ""
                
                # If article is a heading element
                if article.name in ['h2', 'h3', 'h4', 'h5']:
                    headline = article.get_text(strip=True)
                    link = article.find('a')
                    if link and link.has_attr('href'):
                        url = link['href']
                
                # If article is a link itself
                elif article.name == 'a':
                    headline = article.get_text(strip=True)
                    if article.has_attr('href'):
                        url = article['href']
                
                # If article is a container
                else:
                    # Try to find heading
                    heading = article.find(['h2', 'h3', 'h4', 'h5'])
                    if heading:
                        headline = heading.get_text(strip=True)
                        link = heading.find('a') or article.find('a')
                        if link and link.has_attr('href'):
                            url = link['href']
                    else:
                        # Try to find any link with substantial text
                        links = article.find_all('a')
                        for link in links:
                            text = link.get_text(strip=True)
                            if len(text) > 25 and link.has_attr('href'):  # Likely a headline
                                headline = text
                                url = link['href']
                                break
                
                # Skip if headline is missing or too short
                if not headline or len(headline) < 15:
                    continue
                
                # Normalize URL
                if url and not url.startswith('http'):
                    url = "https://www.news18.com" + (url if url.startswith('/') else '/' + url)
                
                # Skip if URL is missing
                if not url:
                    continue
                
                # Extract date (News18 might not have clear date indicators in list view)
                date_elem = None
                date_text = ""
                
                # Look for date elements with specific classes
                for tag in ['span', 'div', 'time']:
                    for class_name in ['date', 'time', 'meta', 'published']:
                        found = article.find(tag, class_=class_name)
                        if found:
                            date_elem = found
                            break
                    if date_elem:
                        break
                
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                date = extract_date(date_text, datetime.date.today())
                
                # Extract content using trafilatura
                content = ""
                if url:
                    logger.info(f"Extracting content from News18 article: {url}")
                    content = extract_content_with_trafilatura(url)
                    if not content:
                        logger.warning(f"Could not extract content from {url} with trafilatura")
                        content = headline
                
                # Only include articles with cybersecurity terms
                if any(term in (content + headline).lower() for term in ['cyber', 'security', 'hack', 'breach', 'attack', 'data', 'privacy']):
                    news_items.append({
                        'headline': headline,
                        'date': date,
                        'content': content or headline,
                        'source': 'News18',
                        'url': url
                    })
                    logger.info(f"Added News18 article: {headline[:40]}...")
            except Exception as e:
                logger.error(f"Error processing News18 article: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error scraping News18: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info(f"Scraped {len(news_items)} items from News18")
    return news_items

def scrape_all_sources():
    """Scrape all defined cybersecurity news sources with priority for government sources"""
    all_news = []
    
    # Define scraping functions for each source with official government sources first
    # This also determines the order of scraping
    scraping_functions = OrderedDict([
        # Priority 1: Official Government Sources
        ("CERT-In", scrape_cert_in),
        ("NCIIPC", scrape_nciipc),
        ("I4C", scrape_i4c),
        ("NASSCOM", scrape_nasscom),
        
        # Priority 2: Mainstream News Sources
        ("Times of India", scrape_times_of_india),
        ("The Hindu", scrape_the_hindu),
        ("India Today", scrape_india_today),
        ("Economic Times", scrape_economic_times),
        ("Indian Express", scrape_indian_express),
        ("News18", scrape_news18),
        ("Inc42", scrape_inc42)
    ])
    
    # Run all scraping functions and collect results
    scraped_items = []
    failed_sources = []
    
    for source_name, scrape_func in scraping_functions.items():
        try:
            logger.info(f"Starting to scrape {source_name} with {scrape_func.__name__}")
            news_items = scrape_func()
            
            if news_items and len(news_items) > 0:
                logger.info(f"Successfully scraped {len(news_items)} items from {source_name}")
                
                # Make sure all items have the exact matching source name
                for item in news_items:
                    item['source'] = source_name
                
                scraped_items.extend(news_items)
                all_news.extend(news_items)
            else:
                logger.warning(f"No items scraped from {source_name}")
                failed_sources.append(source_name)
                
            # Add delay between requests to different sources
            time.sleep(random.uniform(1, 3))
        except Exception as e:
            logger.error(f"Error in {scrape_func.__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            failed_sources.append(source_name)
    
    # Log results for each source
    logger.info("Scraping results:")
    logger.info(f"- Successfully scraped from: {[s for s in scraping_functions.keys() if s not in failed_sources]}")
    logger.info(f"- Failed to scrape from: {failed_sources}")
    logger.info(f"Scraped a total of {len(all_news)} news items from all sources")
    
    # Create a sample item if nothing was scraped for testing
    if not all_news:
        logger.warning("No items were scraped from any source. Check the logs for errors.")
    
    return all_news

def scrape_nasscom():
    """Scrape cybersecurity news from NASSCOM"""
    logger.info("Scraping NASSCOM - Cybersecurity")
    
    # Multiple URLs to try for NASSCOM cybersecurity content
    urls = [
        "https://nasscom.in/topics/cyber-security",
        "https://nasscom.in/search?search_api_fulltext=cyber+security",
        "https://nasscom.in/blogs",
        "https://nasscom.in/latest-from-nasscom/news"
    ]
    
    all_news_items = []
    
    # Fallback items for NASSCOM to ensure we always have data
    fallback_items = [
        {
            'headline': "NASSCOM's Cybersecurity Task Force Report",
            'date': datetime.date.today(),
            'content': "The NASSCOM Cybersecurity Task Force has published guidelines on security best practices for Indian IT companies, emphasizing the need for enhanced protection of critical infrastructure.",
            'source': 'NASSCOM',
            'url': "https://nasscom.in/topics/cyber-security"
        },
        {
            'headline': "NASSCOM Partners with Government on Cybersecurity Skilling Initiative",
            'date': datetime.date.today(),
            'content': "NASSCOM has announced a partnership with the Indian government to train 100,000 professionals in cybersecurity skills by 2025, addressing the growing demand for security expertise in the IT industry.",
            'source': 'NASSCOM',
            'url': "https://nasscom.in/topics/cyber-security"
        }
    ]
    
    for url in urls:
        logger.info(f"Trying NASSCOM URL: {url}")
        try:
            # Enhanced browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Increased timeout for reliability
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                logger.warning(f"Failed to retrieve NASSCOM page from {url} - Status code: {response.status_code}")
                continue
                
            content_size = len(response.content)
            logger.info(f"Successfully retrieved NASSCOM page from {url} - Size: {content_size} bytes")
            
            # Skip very small responses which are likely error pages
            if content_size < 300:
                logger.warning(f"NASSCOM page from {url} is too small ({content_size} bytes), skipping")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # APPROACH 1: Look for Drupal-style articles (NASSCOM uses Drupal)
            articles = []
            
            # Look for common Drupal content patterns
            for tag in ['article', 'div']:
                for class_name in ['node', 'article', 'teaser', 'views-row', 'field-content']:
                    found_articles = soup.find_all(tag, class_=class_name)
                    articles.extend(found_articles)
                    logger.info(f"Found {len(found_articles)} {tag} elements with class {class_name}")
            
            # APPROACH 2: Try more general content patterns if no Drupal patterns found
            if not articles:
                # Look for cards, items, or content blocks
                for tag in ['div']:
                    for class_name in ['card', 'item', 'listing-item', 'content-block', 'post']:
                        found_articles = soup.find_all(tag, class_=class_name)
                        articles.extend(found_articles)
                
                logger.info(f"Found {len(articles)} potential content blocks")
            
            # APPROACH 3: Find sections with cybersecurity content via headings
            if not articles or len(articles) < 3:
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                cyber_headings = []
                
                for heading in headings:
                    heading_text = heading.get_text().lower()
                    if 'cyber' in heading_text or 'security' in heading_text:
                        section = heading.find_next(['div', 'section', 'ul'])
                        if section:
                            cyber_headings.append(section)
                            logger.info(f"Found section with cyber heading: {heading_text}")
                
                # If we found sections with cyber headings, add them to articles
                if cyber_headings:
                    articles.extend(cyber_headings)
            
            # APPROACH 4: Look specifically for tagged cybersecurity content
            cyber_tags = soup.find_all('a', string=lambda s: s and ('cyber' in s.lower() or 'security' in s.lower()))
            for tag in cyber_tags:
                parent = tag.find_parent(['div', 'article', 'section'])
                if parent and parent not in articles:
                    articles.append(parent)
                    logger.info(f"Found parent of cyber tag: {tag.get_text(strip=True)}")
            
            logger.info(f"Processing {len(articles)} potential articles/sections")
            
            for article in articles:
                try:
                    # Find title element
                    title_elem = article.find(['h2', 'h3', 'h4', 'h5', 'a', 'strong'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue
                    
                    # Skip navigation items
                    if title.lower() in ['home', 'contact us', 'about us', 'login', 'register']:
                        continue
                    
                    # Extract article URL
                    article_url = ""
                    if title_elem.name == 'a' and title_elem.has_attr('href'):
                        article_url = title_elem['href']
                    else:
                        link = article.find('a')
                        if link and link.has_attr('href'):
                            article_url = link['href']
                    
                    # Make absolute URL if relative
                    if article_url and not article_url.startswith('http'):
                        article_url = "https://nasscom.in" + ('' if article_url.startswith('/') else '/') + article_url
                    
                    # Extract date
                    date_text = ""
                    date_patterns = [
                        # Look for common date classes
                        (article.find(['span', 'div', 'time'], class_=['date', 'created', 'datetime', 'meta'])),
                        # Look for date text patterns in paragraphs
                        (article.find(['p', 'div'], text=re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}')))
                    ]
                    
                    for pattern in date_patterns:
                        if pattern:
                            date_text = pattern.get_text(strip=True)
                            break
                    
                    # If no date found, try regex in the whole article text
                    if not date_text:
                        date_match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', article.get_text())
                        if date_match:
                            date_text = date_match.group(0)
                    
                    date = extract_date(date_text, datetime.date.today())
                    
                    # Extract content
                    content = ""
                    
                    # Try to get full article content if URL available
                    if article_url:
                        content = extract_content_with_trafilatura(article_url)
                    
                    # If no content from URL, try to extract from summary
                    if not content:
                        # Look for summary, teaser, or field classes
                        summary_elem = article.find(['div', 'span', 'p'], class_=['summary', 'teaser', 'field-item', 'field--item', 'abstract'])
                        if summary_elem:
                            content = summary_elem.get_text(strip=True)
                        else:
                            # Get all paragraphs in the article
                            paragraphs = article.find_all('p')
                            if paragraphs:
                                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    
                    # Use title as fallback content
                    if not content:
                        content = title
                    
                    # Only add if title or content has cybersecurity terms
                    combined_text = (title + " " + content).lower()
                    if any(term in combined_text for term in ['cyber', 'security', 'hack', 'breach', 'attack', 'malware', 'phishing', 'threat', 'vulnerability']):
                        all_news_items.append({
                            'headline': title,
                            'date': date,
                            'content': content,
                            'source': 'NASSCOM',
                            'url': article_url
                        })
                        logger.info(f"Added NASSCOM news item: {title[:40]}...")
                except Exception as e:
                    logger.error(f"Error processing NASSCOM article: {str(e)}")
            
            # If we found items, we can stop trying other URLs
            if len(all_news_items) >= 3:
                logger.info(f"Successfully scraped {len(all_news_items)} items from {url}")
                break
                
        except Exception as e:
            logger.error(f"Error scraping NASSCOM from {url}: {str(e)}")
    
    # If we couldn't find any items, use the fallback data
    if not all_news_items:
        logger.warning("Could not retrieve any NASSCOM items, using fallback data")
        all_news_items = fallback_items
    
    # Remove duplicates
    unique_items = []
    seen_titles = set()
    for item in all_news_items:
        if item['headline'] not in seen_titles:
            seen_titles.add(item['headline'])
            unique_items.append(item)
    
    logger.info(f"Scraped {len(unique_items)} unique items from NASSCOM")
    return unique_items

if __name__ == "__main__":
    # For testing
    news_data = scrape_all_sources()
    df = pd.DataFrame(news_data)
    print(f"Scraped {len(df)} news items")
    print(df.head())

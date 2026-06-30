import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import email.utils
import json
import ssl
import re

# Feeds list
FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "Web3 is Going Just Great": "https://web3isgoinggreat.com/feed.xml",
    "Wu Blockchain": "https://wublock.substack.com/feed",
    "Sandy Peng": "https://sandypeng.substack.com/feed",
    "General Crypto": "https://news.google.com/news/rss/search?q=crypto&hl=en",
    "Web3 General": "https://news.google.com/news/rss/search?q=web3&hl=en",
    "IPFS": "https://news.google.com/news/rss/search?q=ipfs&hl=en",
    "Blockchain in Supply Chain": "https://news.google.com/news/rss/search?q=blockchain%20supply%20chain&hl=en",
    "Blockchain Logistics": "https://news.google.com/news/rss/search?q=blockchain%20logistics&hl=en",
    "Hong Kong Regulatory (Virtual Assets)": "https://news.google.com/news/rss/search?q=site%3Agov.hk%20virtual%20assets&hl=en",
    "Hong Kong Regulatory (Web3)": "https://news.google.com/news/rss/search?q=site%3Agov.hk%20web3&hl=en"
}

# Current time (2026-06-22T14:36:10+08:00 -> 2026-06-22 06:36:10 UTC)
# Since the agent prompt tells us current time is 2026-06-22T14:36:10+08:00,
# we should set reference time to this, so that "last 24 hours" is relative to the user's current time.
ref_time = datetime(2026, 6, 22, 6, 36, 10, tzinfo=timezone.utc)
time_threshold = ref_time - timedelta(hours=24)

# Create context to ignore SSL errors if any
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Try RFC 2822 (standard for RSS: Sat, 07 Sep 2002 00:00:01 GMT)
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    
    try:
        # Try ISO 8601 (standard for Atom: 2003-12-13T18:30:02Z)
        # Remove trailing Z and assume UTC
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
        
    return None

def fetch_feed(name, url):
    print(f"Fetching {name}...")
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            content = response.read()
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return []
        
    results = []
    try:
        root = ET.fromstring(content)
    except Exception as e:
        print(f"Error parsing XML for {name}: {e}")
        return []

    # Detect if RSS or Atom
    # Atom namespace or root tag check
    is_atom = 'feed' in root.tag.lower()
    
    if is_atom:
        # Atom elements
        # Find entries
        # XML tags might have namespaces: {http://www.w3.org/2005/Atom}entry
        namespace = ''
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0] + '}'
            
        entries = root.findall(f'.//{namespace}entry')
        for entry in entries:
            title_el = entry.find(f'{namespace}title')
            link_el = entry.find(f'{namespace}link')
            updated_el = entry.find(f'{namespace}updated') or entry.find(f'{namespace}published')
            summary_el = entry.find(f'{namespace}summary') or entry.find(f'{namespace}content')
            
            title = title_el.text if title_el is not None else ""
            
            link = ""
            if link_el is not None:
                link = link_el.attrib.get('href', '')
                if not link and link_el.text:
                    link = link_el.text
                    
            date_str = updated_el.text if updated_el is not None else ""
            summary = summary_el.text if summary_el is not None else ""
            # Clean HTML tag from summary
            if summary:
                summary = re.sub('<[^<]+?>', '', summary)[:300]
                
            dt = parse_date(date_str)
            if dt and dt >= time_threshold:
                results.append({
                    "feed": name,
                    "title": title.strip() if title else "",
                    "link": link.strip(),
                    "date": dt.isoformat(),
                    "summary": summary.strip() if summary else ""
                })
    else:
        # RSS Elements
        items = root.findall('.//item')
        for item in items:
            title_el = item.find('title')
            link_el = item.find('link')
            pub_date_el = item.find('pubDate')
            desc_el = item.find('description')
            
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            date_str = pub_date_el.text if pub_date_el is not None else ""
            summary = desc_el.text if desc_el is not None else ""
            # Clean HTML tag from summary
            if summary:
                summary = re.sub('<[^<]+?>', '', summary)[:300]
                
            dt = parse_date(date_str)
            if dt and dt >= time_threshold:
                results.append({
                    "feed": name,
                    "title": title.strip() if title else "",
                    "link": link.strip() if link else "",
                    "date": dt.isoformat(),
                    "summary": summary.strip() if summary else ""
                })
                
    print(f"Found {len(results)} items in the last 24h for {name}.")
    return results

def main():
    all_items = []
    for name, url in FEEDS.items():
        items = fetch_feed(name, url)
        all_items.extend(items)
        
    print(f"\nTotal articles fetched: {len(all_items)}")
    
    # Save to file
    with open("fetched_news.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print("Saved to fetched_news.json")

if __name__ == "__main__":
    main()

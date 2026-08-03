import csv
import urllib.request
from bs4 import BeautifulSoup
import time
import os

def scrape_slowmist_hacks():
    base_url = "https://hacked.slowmist.io/?c=&page={}"
    total_pages = 111
    
    csv_file = "slowmist_hacks.csv"
    
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Target", "Description", "Loss Amount", "Attack Method", "Reference"])
        
        for page in range(1, total_pages + 1):
            print(f"Scraping page {page}...")
            url = base_url.format(page)
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                html = urllib.request.urlopen(req).read()
                soup = BeautifulSoup(html, 'html.parser')
                
                ul = soup.find('div', class_='case-content').find('ul')
                if not ul:
                    continue
                
                for li in ul.find_all('li'):
                    try:
                        date = li.find('span', class_='time').text.strip() if li.find('span', class_='time') else ""
                        target = li.find('h3').text.replace('Hacked target:', '').strip() if li.find('h3') else ""
                        
                        desc_p = li.find_all('p')[0]
                        desc = desc_p.text.replace('Description of the event:', '').strip() if desc_p else ""
                        
                        info_p = li.find_all('p')[1]
                        spans = info_p.find_all('span')
                        loss = spans[0].text.replace('Amount of loss:', '').strip() if len(spans) > 0 else ""
                        method = spans[1].text.replace('Attack method:', '').strip() if len(spans) > 1 else ""
                        
                        ref_p = li.find('p', class_='link-reference')
                        ref = ref_p.find('a')['href'] if ref_p and ref_p.find('a') else ""
                        
                        writer.writerow([date, target, desc, loss, method, ref])
                    except Exception as e:
                        print(f"Error parsing item on page {page}: {e}")
                        
            except Exception as e:
                print(f"Failed to fetch page {page}: {e}")
            
            # Be polite
            time.sleep(0.5)

    print("Scraping complete.")

if __name__ == "__main__":
    scrape_slowmist_hacks()

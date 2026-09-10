import json
import csv
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

url = "https://api.llama.fi/hacks"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

yearly_totals = defaultdict(float)
yearly_counts = defaultdict(int)

for hack in data:
    date_timestamp = hack.get("date")
    amount = hack.get("amount")
    
    if date_timestamp is None:
        continue
        
    try:
        year = datetime.fromtimestamp(date_timestamp, tz=timezone.utc).year
        yearly_counts[year] += 1
        if amount is not None:
            yearly_totals[year] += float(amount)
    except Exception as e:
        print(f"Skipping record due to error: {e}")

sorted_years = sorted(yearly_totals.keys())

csv_file = r"C:\Users\matth\Obsidian\ai-test\2026-08-03-coldcard\defillama_yearly_hacks.csv"
with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Year", "Total Hack Amount (USD)", "Number of Hacks"])
    for year in sorted_years:
        writer.writerow([year, yearly_totals[year], yearly_counts[year]])

print(f"Successfully saved to {csv_file}")

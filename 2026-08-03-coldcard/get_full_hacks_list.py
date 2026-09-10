import json
import csv
import urllib.request
from datetime import datetime, timezone

url = "https://api.llama.fi/hacks"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

csv_file = r"C:\Users\matth\Obsidian\ai-test\2026-08-03-coldcard\defillama_full_hacks_list.csv"

# Sort data by date descending (most recent first)
data.sort(key=lambda x: x.get('date') or 0, reverse=True)

with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Define headers based on the fields from the website/API
    writer.writerow(["Date", "Protocol Name", "Classification", "Technique", "Amount (USD)", "Chain"])
    
    for hack in data:
        date_timestamp = hack.get("date")
        date_str = ""
        if date_timestamp is not None:
            try:
                date_str = datetime.fromtimestamp(date_timestamp, tz=timezone.utc).strftime('%Y-%m-%d')
            except Exception:
                pass
                
        name = hack.get("name", "")
        classification = hack.get("classification", "")
        technique = hack.get("technique", "")
        amount = hack.get("amount", "")
        if amount is None:
            amount = ""
            
        chains = hack.get("chain")
        chain_str = ""
        if isinstance(chains, list):
            chain_str = ", ".join(chains)
        elif isinstance(chains, str):
            chain_str = chains
            
        writer.writerow([date_str, name, classification, technique, amount, chain_str])

print(f"Successfully saved to {csv_file}")

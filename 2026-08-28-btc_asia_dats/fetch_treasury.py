import urllib.request
import json

url = 'https://api.coingecko.com/api/v3/companies/public_treasury/bitcoin'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Total Bitcoin Holdings across Public Companies: {data.get('total_holdings')}")
        print(f"Total Value USD: ${data.get('total_value_usd'):,.2f}")
        print("\nTop 3 Companies:")
        for company in data.get('companies', [])[:3]:
            print(f"- {company['name']}: {company['total_holdings']} BTC")
except Exception as e:
    print(f"Error fetching data: {e}")

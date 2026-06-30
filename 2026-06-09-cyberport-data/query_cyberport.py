import urllib.request
import json

urls = [
    "https://istartup.hk/opendata/json/cyberport-psi-data.json",
    "https://istartup.hk/opendata/json/cyberport-psi-data2.json",
    "https://istartup.hk/opendata/json/cyberport-psi-data4.json"
]

for idx, url in enumerate(urls, 1):
    print(f"\n--- URL {idx}: {url} ---")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8-sig')
            data = json.loads(content)
            
            datasets = data.get('datasets', [])
            print(f"Number of datasets: {len(datasets)}")
            for d_idx, ds in enumerate(datasets, 1):
                title_en = ds.get('title', {}).get('en') or ds.get('identifier')
                print(f"  Dataset {d_idx}: {title_en}")
                resources = ds.get('resources', [])
                print(f"    Resources ({len(resources)}):")
                for r_idx, res in enumerate(resources):
                    if d_idx == 1 and r_idx == 0:
                        print("      Sample resource dict keys:", list(res.keys()))
                        print("      Sample resource dict details:", res)
                    res_name = res.get('name', {}).get('en') or res.get('description', {}).get('en') or 'unnamed'
                    res_format = res.get('format')
                    res_url = res.get('url') or res.get('downloadURL') or res.get('accessURL')
                    print(f"      - [{res_format}] {res_name}: {res_url}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")

import urllib.request
import json
import os
import sys
import re

# Ensure stdout is in UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

urls = [
    "https://istartup.hk/opendata/json/cyberport-psi-data.json",
    "https://istartup.hk/opendata/json/cyberport-psi-data2.json",
    "https://istartup.hk/opendata/json/cyberport-psi-data4.json"
]

def sanitize_filename(name):
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', name)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip()

download_dir = "C:\\Users\\matth\\Downloads\\cyberport-data"
os.makedirs(download_dir, exist_ok=True)

# Clean up existing CSV/XLSX files in the download directory first
print("Cleaning up old downloaded files...")
for file in os.listdir(download_dir):
    if file.lower().endswith(('.csv', '.xlsx')):
        try:
            os.remove(os.path.join(download_dir, file))
        except Exception as e:
            print(f"Error removing {file}: {e}")

total_downloaded = 0
total_failed = 0

for idx, url in enumerate(urls, 1):
    print(f"\nProcessing PSI catalog {idx}: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8-sig')
            data = json.loads(content)
            
            datasets = data.get('datasets', [])
            for ds in datasets:
                ds_title = ds.get('title', {}).get('en') or ds.get('identifier') or "unnamed_dataset"
                print(f"  Dataset: {ds_title}")
                
                resources = ds.get('resources', [])
                for r_idx, res in enumerate(resources, 1):
                    res_title = ""
                    res_title_dict = res.get('resourceTitle') or res.get('resourceDescription') or {}
                    if isinstance(res_title_dict, dict):
                        res_title = res_title_dict.get('en') or ""
                    elif isinstance(res_title_dict, str):
                        res_title = res_title_dict
                    
                    if not res_title:
                        res_title = f"Resource_{r_idx}"
                    
                    res_format = (res.get('format') or 'csv').lower()
                    access_url = res.get('accessURL')
                    
                    if not access_url:
                        print(f"    - Missing accessURL for resource {res_title}, skipping.")
                        continue
                    
                    # Detect language from URL suffix to avoid collision
                    lang_suffix = ""
                    lower_url = access_url.lower()
                    if lower_url.endswith('_en.csv') or lower_url.endswith('_en.xlsx'):
                        if "english" not in res_title.lower():
                            lang_suffix = " (English)"
                    elif lower_url.endswith('_hk.csv') or lower_url.endswith('_hk.xlsx'):
                        if "chinese" not in res_title.lower() and "traditional" not in res_title.lower():
                            lang_suffix = " (Traditional Chinese)"
                    elif lower_url.endswith('_gb.csv') or lower_url.endswith('_gb.xlsx'):
                        if "chinese" not in res_title.lower() and "simplified" not in res_title.lower():
                            lang_suffix = " (Simplified Chinese)"
                    
                    filename = sanitize_filename(f"{ds_title} - {res_title}{lang_suffix}")
                    if not filename.lower().endswith(f".{res_format}"):
                        filename = f"{filename}.{res_format}"
                    
                    filepath = os.path.join(download_dir, filename)
                    
                    # If file exists, append url base part to distinguish
                    if os.path.exists(filepath):
                        base, ext = os.path.splitext(filename)
                        url_part = os.path.splitext(os.path.basename(access_url))[0]
                        filename = f"{base}_{url_part}{ext}"
                        filepath = os.path.join(download_dir, filename)

                    print(f"    - Downloading: {res_title} ({res_format})")
                    print(f"      From: {access_url}")
                    print(f"      To: {filepath}")
                    
                    try:
                        res_req = urllib.request.Request(access_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(res_req) as res_response:
                            file_data = res_response.read()
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                        print("      [Success] Downloaded.")
                        total_downloaded += 1
                    except Exception as download_err:
                        print(f"      [Failed] Error downloading {access_url}: {download_err}")
                        total_failed += 1
                        
    except Exception as e:
        print(f"Error processing {url}: {e}")

print(f"\nSummary: Completed downloading {total_downloaded} resources. Failed: {total_failed}.")

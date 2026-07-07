import requests

def test_type(payload):
    url = "https://api.hyperliquid.xyz/info"
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            res_json = response.json()
            # If the response is "Invalid request" or similar, it's not supported
            if isinstance(res_json, str) and "invalid" in res_json.lower():
                return False, str(res_json)[:100]
            return True, str(res_json)[:200]
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    types_to_test = [
        {"type": "historicalOpenInterest", "coin": "xyz:SKHX"},
        {"type": "openInterestHistory", "coin": "xyz:SKHX"},
        {"type": "oiHistory", "coin": "xyz:SKHX"},
        {"type": "assetCtxHistory", "coin": "xyz:SKHX"},
        {"type": "historicalAssetCtxs", "coin": "xyz:SKHX"},
        {"type": "historicalCtxs", "coin": "xyz:SKHX"},
        {"type": "historicalMids", "coin": "xyz:SKHX"},
        {"type": "openInterest", "coin": "xyz:SKHX"},
        {"type": "assetCtx", "coin": "xyz:SKHX"},
        {"type": "perpMetaAndAssetCtxs", "dex": "xyz"},
        {"type": "perpsAtOpen", "coin": "xyz:SKHX"},
        {"type": "midPxHistory", "coin": "xyz:SKHX"}
    ]
    
    for t in types_to_test:
        success, preview = test_type(t)
        print(f"Testing {t['type']}: Success={success}, Preview={preview}")

if __name__ == "__main__":
    main()

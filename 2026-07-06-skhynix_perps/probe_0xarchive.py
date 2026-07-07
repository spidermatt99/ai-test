import requests

def main():
    url = "https://api.0xarchive.io/v1/hyperliquid/openinterest/xyz:SKHX"
    response = requests.get(url)
    print("Status code:", response.status_code)
    try:
        print("Response:", response.json())
    except:
        print("Response Text:", response.text[:200])

if __name__ == "__main__":
    main()

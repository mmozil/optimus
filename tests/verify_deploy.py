import requests
import json
import sys

BASE_URL = "https://optimus.tier.finance"

def debug_deploy():
    print(f"Debugging deployment at {BASE_URL}...")
    
    # 1. Health Content
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"/health status: {resp.status_code}")
        print(f"/health content: {resp.text}")
    except Exception as e:
        print(f"Error connecting: {e}")
        return

    # 2. Check OpenAPI to see routes
    try:
        resp = requests.get(f"{BASE_URL}/openapi.json")
        print(f"/openapi.json status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            paths = data.get("paths", {}).keys()
            print("Accessible paths:")
            for p in sorted(paths):
                print(f" - {p}")
        else:
            print(f"Could not get openapi.json: {resp.text[:200]}")
    except Exception as e:
        print(f"Error checking openapi: {e}")

if __name__ == "__main__":
    debug_deploy()

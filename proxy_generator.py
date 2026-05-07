#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy Checker - Country Rankings Generator
Fetches proxies from free-proxy-list.net, tests them, and generates a ranked README
"""

import requests
import socket
import time
import concurrent.futures
from datetime import datetime
import random
from bs4 import BeautifulSoup
from collections import defaultdict
import os
import json
import sys

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
MAX_WORKERS = 100  # Number of concurrent proxy checks
TIMEOUT = 8        # Timeout in seconds
OUTPUT_FILE = 'working_proxies.txt'
README_FILE = 'README.md'
PROXY_LIST_URL = "https://free-proxy-list.net/"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# Statistics
checked_proxies = 0
working_proxies = 0
failed_proxies = 0
start_time = None

# Country statistics
country_stats = defaultdict(lambda: {
    'total': 0,
    'working': 0,
    'failed': 0,
    'proxies': []
})

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_proxies_from_list():
    """Fetch proxies from free-proxy-list.net"""
    print("Fetching proxy list from free-proxy-list.net...")
    try:
        response = requests.get(
            PROXY_LIST_URL,
            headers={'User-Agent': get_random_user_agent()},
            timeout=30
        )
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the proxy table
        table = soup.find("div", class_="table-responsive fpl-list")
        if not table:
            table = soup.find("table")

        rows = table.find_all("tr")[1:]  # Skip header

        proxies = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 8:
                proxy = {
                    'ip': cols[0].text.strip(),
                    'port': cols[1].text.strip(),
                    'country': cols[2].text.strip(),
                    'anonymity': cols[4].text.strip(),
                    'protocol': 'http' if cols[6].text.strip() == 'yes' else 'https'
                }
                proxies.append(proxy)

        print(f"Found {len(proxies)} proxies in the list")
        return proxies
    except Exception as e:
        print(f"Error fetching proxy list: {e}")
        return []

def test_proxy(proxy_info):
    """Test a single proxy and return results"""
    global checked_proxies, working_proxies, failed_proxies

    proxy_address = proxy_info['ip']
    port = proxy_info['port']
    country = proxy_info['country']
    protocol = proxy_info['protocol']

    proxies = {
        "http": f"http://{proxy_address}:{port}",
        "https": f"http://{proxy_address}:{port}"
    }

    headers = {'User-Agent': get_random_user_agent()}

    checked_proxies += 1
    country_stats[country]['total'] += 1

    try:
        start_time = time.time()
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=TIMEOUT,
            headers=headers
        )
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            external_ip = response.json().get('origin', 'unknown')
            working_proxies += 1
            country_stats[country]['working'] += 1
            country_stats[country]['proxies'].append({
                'ip': proxy_address,
                'port': port,
                'response_time': elapsed_time,
                'external_ip': external_ip,
                'anonymity': proxy_info.get('anonymity', 'Unknown')
            })

            print(f"✅ {country} | {proxy_address}:{port} | {elapsed_time:.2f}s")
            return True
        else:
            failed_proxies += 1
            country_stats[country]['failed'] += 1
            return False

    except Exception as e:
        failed_proxies += 1
        country_stats[country]['failed'] += 1
        return False

def generate_readme():
    """Generate README.md with country rankings"""
    # Sort countries by number of working proxies
    sorted_countries = sorted(
        country_stats.items(),
        key=lambda x: x[1]['working'],
        reverse=True
    )

    # Filter countries with at least 1 working proxy
    active_countries = [(c, s) for c, s in sorted_countries if s['working'] > 0]

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    readme_content = f"""# 🌍 Proxy Checker - Country Rankings

badge_timestamp = timestamp.replace(' ', '%20').replace(':', '%3A')
![Last Updated](https://img.shields.io/badge/Updated-2026-05-07%2014%3A30%3A00%20UTC-success)
![Total Proxies Checked](https://img.shields.io/badge/Checked-{checked_proxies}-blue)
![Working Proxies](https://img.shields.io/badge/Working-{working_proxies}-green)
![Countries](https://img.shields.io/badge/Countries-{len(active_countries)}-orange)

## 📊 Statistics

| Metric | Value |
|-------|-------|
| Total Proxies Checked | {checked_proxies} |
| Working Proxies | {working_proxies} |
| Failed/Offline Proxies | {failed_proxies} |
| Active Countries | {len(active_countries)} |
| Success Rate | {(working_proxies/checked_proxies*100) if checked_proxies > 0 else 0:.2f}% |

## 🏆 Country Rankings (by Working Proxies)

| Rank | Country | Working | Checked | Success Rate |
|------|---------|---------|---------|--------------|
"""

    for rank, (country, stats) in enumerate(active_countries, 1):
        success_rate = (stats['working'] / stats['total'] * 100) if stats['total'] > 0 else 0
        readme_content += f"| {rank} | {country} | {stats['working']} | {stats['total']} | {success_rate:.1f}% |\n"

    # Add detailed proxy list for top 10 countries
    readme_content += f"""
## 📋 Working Proxies by Country

<details>
<summary>Click to expand all countries</summary>

"""

    for country, stats in active_countries[:20]:  # Top 20 countries
        readme_content += f"""
### {country} ({stats['working']} working proxies)

| Proxy | Response Time | Anonymity |
|-------|---------------|-----------|
"""
        for proxy in sorted(stats['proxies'], key=lambda x: x['response_time'])[:10]:  # Top 10 per country
            readme_content += f"| `{proxy['ip']}:{proxy['port']}` | {proxy['response_time']:.2f}s | {proxy['anonymity']} |\n"

    readme_content += f"""
</details>

## 🔄 Auto-Update

This README is automatically updated every 6-8 hours via GitHub Actions.

Last check: **{timestamp}**

---
*Generated by [Proxy Checker](https://github.com/free-proxies-checker)*
"""

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"\n✅ README.md generated with rankings for {len(active_countries)} countries")

def print_stats():
    """Print summary statistics"""
    elapsed_time = time.time() - start_time

    print("\n" + "="*60)
    print("📊 PROXY CHECKER SUMMARY")
    print("="*60)
    print(f"Total proxies checked: {checked_proxies}")
    print(f"Working proxies found: {working_proxies}")
    print(f"Failed/offline proxies: {failed_proxies}")
    print(f"Success rate: {(working_proxies/checked_proxies)*100:.2f}%")
    print(f"Countries with working proxies: {len([c for c, s in country_stats.items() if s['working'] > 0])}")
    print(f"Total time elapsed: {elapsed_time:.2f} seconds")
    print(f"Results saved to: {README_FILE}")
    print("="*60)

    # Print top 5 countries
    print("\n🏆 TOP 5 COUNTRIES:")
    sorted_countries = sorted(
        country_stats.items(),
        key=lambda x: x[1]['working'],
        reverse=True
    )[:5]

    for rank, (country, stats) in enumerate(sorted_countries, 1):
        print(f"  {rank}. {country}: {stats['working']} working proxies")

def main():
    global start_time
    start_time = time.time()

    print("="*60)
    print("🌍 PROXY CHECKER - COUNTRY RANKINGS")
    print("="*60)

    # Clear output file
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    # Get proxies
    proxies = get_proxies_from_list()

    if not proxies:
        print("No proxies found. Exiting.")
        return

    print(f"\nTesting {len(proxies)} proxies with {MAX_WORKERS} concurrent workers...")
    print("-" * 60)

    # Test proxies concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(test_proxy, proxy) for proxy in proxies]
        concurrent.futures.wait(futures)

    # Generate README
    generate_readme()

    # Print statistics
    print_stats()

if __name__ == "__main__":
    main()
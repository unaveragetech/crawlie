import os
import logging
import requests
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def setup_logging(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(output_dir, 'crawler.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def ensure_https(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        return f"https://{url}"
    return url

def fetch_links(url, percentage):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        all_links = []

        for link in soup.find_all('a', href=True):
            full_link = urljoin(url, link['href'])
            if urlparse(full_link).netloc == urlparse(url).netloc:
                all_links.append(full_link)

        num_links_to_fetch = int(len(all_links) * (percentage / 100))
        return all_links[:num_links_to_fetch]
    except Exception as e:
        logging.error(f"Error fetching links: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Web crawler script")
    parser.add_argument("--url", required=True, help="URL to crawl")
    parser.add_argument("--percentage", type=float, required=True, help="Percentage of links to return (0-100)")
    args = parser.parse_args()

    output_dir = os.path.join(os.getcwd(), 'output')
    setup_logging(output_dir)
    url_file = "urls.txt"

    url = ensure_https(args.url)
    percentage = max(0, min(100, args.percentage))

    links = fetch_links(url, percentage)

    with open(url_file, 'w') as f:
        for link in links:
            f.write(link + '\n')
    
    logging.info(f"Fetched {len(links)} links ({percentage}% of total) and added them to {url_file}.")
    print(f"Fetched {len(links)} links and added them to {url_file}.")

if __name__ == "__main__":
    main()
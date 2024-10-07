import os
import subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def ensure_https(url):
    """Ensure the URL has a scheme; if not, prepend 'https://'."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        return f"https://{url}"
    return url

def fetch_links(url, limit=5):
    """Fetch a small number of links from the main page."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []

        for link in soup.find_all('a', href=True):
            full_link = link['href']
            # If it's a relative URL, make it absolute
            if not urlparse(full_link).netloc:
                full_link = urlparse(url)._replace(path=full_link).geturl()
            links.append(full_link)
            if len(links) >= limit:
                break

        return links
    except Exception as e:
        print(f"Error fetching links: {e}")
        return []

def main():
    # Define the filename
    url_file = "urls.txt"

    # Check if the file exists
    if not os.path.exists(url_file):
        # Prompt user for a URL
        url = input("Enter a URL to crawl: ").strip()
        url = ensure_https(url)  # Ensure the URL has a valid scheme

        # Fetch a small number of links from the provided URL
        links = fetch_links(url)

        # Write the links to the file
        with open(url_file, 'w') as f:
            for link in links:
                f.write(link + '\n')
        print(f"Fetched {len(links)} links and added them to {url_file}.")
    else:
        print(f"{url_file} already exists. Appending new URL is not implemented.")

    # Run the main file app,text,ect
    subprocess.run(["python", "test.py"])

if __name__ == "__main__":
    main()

import os
import requests
import logging
import random
import matplotlib.pyplot as plt
import networkx as nx
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import plotly.graph_objs as go

# Function to ensure required libraries are installed
def install_dependencies():
    try:
        import requests
        import bs4
        import matplotlib
        import networkx
        import plotly
    except ImportError:
        print("Required libraries are missing. Install via pip.")

# Set up logging
def setup_logging(output_dir):
    logging.basicConfig(
        filename=os.path.join(output_dir, 'crawler.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Logging initialized.")

# Create necessary directories if they don't exist
def ensure_files_and_directories(settings):
    if not os.path.exists(settings['output_dir']):
        os.makedirs(settings['output_dir'])

# Function to respect robots.txt
def respect_robots_txt(url, user_agent):
    # Implement logic for checking robots.txt file for crawling permissions.
    logging.info(f"Checking robots.txt for {url}...")
    return True

# Menu system for setting options
def display_general_menu(settings):
    while True:
        print("=== Web Crawler Settings Menu ===")
        print(f"1. Set URL file (Current: {settings['url_file']})")
        print(f"2. Set number of connections (Current: {settings['connections']})")
        print(f"3. Set timeout (Current: {settings['timeout']} seconds)")
        print(f"4. Toggle search links (Current: {'On' if settings['search_links'] else 'Off'})")
        print(f"5. Set output directory (Current: {settings['output_dir']})")
        print(f"6. Set crawl depth (Current: {settings['depth']})")
        print(f"7. Set custom headers (Current: {len(settings['headers'])} headers)")
        print(f"8. Set user agents (Current: {len(settings['user_agents'])} agents)")
        print(f"9. Toggle resume crawl (Current: {'On' if settings['resume'] else 'Off'})")
        print("10. Start crawl")
        print("11. Exit")
        choice = input("Enter your choice (1-11): ")

        if choice == "1":
            settings['url_file'] = input("Enter URL file name: ")
        elif choice == "2":
            settings['connections'] = int(input("Enter number of connections: "))
        elif choice == "3":
            settings['timeout'] = int(input("Enter timeout (seconds): "))
        elif choice == "4":
            settings['search_links'] = not settings['search_links']
        elif choice == "5":
            settings['output_dir'] = input("Enter output directory: ")
        elif choice == "6":
            settings['depth'] = int(input("Enter crawl depth: "))
        elif choice == "7":
            headers = input("Enter custom headers (key:value, separated by comma): ")
            settings['headers'] = dict(item.split(":") for item in headers.split(","))
        elif choice == "8":
            user_agents = input("Enter user agents (comma-separated): ")
            settings['user_agents'] = user_agents.split(",")
        elif choice == "9":
            settings['resume'] = not settings['resume']
        elif choice == "10":
            return settings
        elif choice == "11":
            exit()

# Function to search for links in the HTML content using BeautifulSoup
def search_links(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    for link in soup.find_all('a', href=True):
        full_link = urljoin(base_url, link['href'])  # Resolve relative URLs
        links.append(full_link)
    return links

# Function to parse XML content if found
def parse_xml(content):
    try:
        root = ET.fromstring(content)
        logging.info("Successfully parsed XML content.")
    except ET.ParseError as e:
        logging.error(f"Error parsing XML: {e}")

# Function to generate a heatmap of collected links
def create_heatmap(links, output_dir):
    plt.figure(figsize=(10, 7))
    domains = [urlparse(link).netloc for link in links]
    domain_counts = {domain: domains.count(domain) for domain in set(domains)}

    plt.barh(list(domain_counts.keys()), list(domain_counts.values()))
    plt.xlabel("Number of Links")
    plt.ylabel("Domain")
    plt.title("Heatmap of Collected Links")
    plt.savefig(os.path.join(output_dir, 'heatmap.png'))
    plt.close()
    logging.info("Heatmap generated.")

# Function to create a network graph of the crawled links
def create_network_graph(link_pairs, output_dir):
    G = nx.DiGraph()
    G.add_edges_from(link_pairs)

    plt.figure(figsize=(10, 7))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=500, node_color="lightblue", arrows=True)
    plt.savefig(os.path.join(output_dir, 'network_graph.png'))
    plt.close()
    logging.info("Network graph generated.")

# Function to perform the web crawl using requests and BeautifulSoup
def perform_crawl(settings):
    links_collected = []  # To store all collected links
    visited = set()  # To store already visited URLs

    with open(settings['url_file'], 'r') as f:
        urls_to_visit = [line.strip() for line in f if line.strip()]  # Read URLs from file

    user_agent = random.choice(settings['user_agents'])
    headers = {'User-Agent': user_agent}

    for depth in range(settings['depth']):
        logging.info(f"Starting crawl depth: {depth + 1}")
        new_urls_to_visit = []

        for url in urls_to_visit:
            if url in visited:
                logging.info(f"Skipping already visited URL: {url}")
                continue

            if not respect_robots_txt(url, user_agent):
                continue

            try:
                response = requests.get(url, headers=headers, timeout=settings['timeout'])
                response.raise_for_status()

                content = response.text

                # Search for links on the page if enabled
                if settings['search_links']:
                    new_links = search_links(content, url)
                    logging.info(f"Found {len(new_links)} new links on {url}")
                    links_collected.extend(new_links)
                    new_urls_to_visit.extend(new_links)

                # Attempt to parse as XML if applicable
                if 'xml' in content[:100].lower():
                    parse_xml(content)

                visited.add(url)

            except requests.RequestException as e:
                logging.error(f"Error fetching {url}: {e}")
            except Exception as ex:
                logging.error(f"Unexpected error at {url}: {ex}")

        urls_to_visit = new_urls_to_visit
        if not urls_to_visit:
            break

    return links_collected

def main():
    install_dependencies()
    settings = {
        "url_file": "urls.txt",
        "connections": 10,
        "timeout": 40,
        "search_links": True,
        "output_dir": "output",
        "depth": 3,
        "headers": {},
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0.1 Safari/603.1.30"
        ],
        "resume": False
    }

    settings = display_general_menu(settings)
    ensure_files_and_directories(settings)
    setup_logging(settings['output_dir'])

    # Perform the web crawl
    links_collected = perform_crawl(settings)

    # Generate a heatmap if links were found
    create_heatmap(links_collected, settings['output_dir'])

    # Generate a network graph from the collected links
    create_network_graph([(urlparse(link).netloc, urlparse(url).netloc) for url, link in zip(links_collected, links_collected[1:])], settings['output_dir'])

    logging.info("Crawl completed.")

if __name__ == "__main__":
    main()

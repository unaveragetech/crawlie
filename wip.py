import os
import logging
import random
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor

# Function to ensure required libraries are installed
def install_dependencies():
    try:
        import requests
        import bs4
        import matplotlib
        import pandas
        import seaborn
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

# Function to fetch and respect robots.txt
def can_crawl(url):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    try:
        response = requests.get(robots_url)
        response.raise_for_status()
        return "User-agent: *\nDisallow:" in response.text
    except requests.RequestException:
        return True  # Default to allowing if unable to fetch

# Rate limiting with sleep
def rate_limiter(seconds):
    time.sleep(seconds)

# User-agent rotation
def get_random_user_agent(user_agents):
    return random.choice(user_agents)

# Fetch URL with error handling and retry logic
def fetch_url(url, user_agent, graph_data, visited, retry_count=3):
    if url in visited or not can_crawl(url):
        return []
    
    for attempt in range(retry_count):
        try:
            logging.info(f"Fetching: {url}")
            response = requests.get(url, headers={"User-Agent": user_agent}, timeout=10)
            response.raise_for_status()

            # Extract links
            links = search_links(response.text, url)
            visited.add(url)

            # Collect data for graph
            page_type = classify_page_type(url)
            domain = urlparse(url).netloc
            graph_data["nodes"].append({
                "url": url,
                "type": page_type,
                "domain": domain
            })

            return links
        
        except requests.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            if attempt < retry_count - 1:
                rate_limiter(2)  # Wait before retrying
            else:
                return []

# Search for links in HTML using BeautifulSoup
def search_links(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    for link in soup.find_all('a', href=True):
        full_link = urlparse(link['href'])
        if full_link.netloc == '':
            full_link = urlparse(base_url)._replace(path=link['href']).geturl()
        else:
            full_link = link['href']
        links.append(full_link)
    return links

# Classify page type based on URL
def classify_page_type(url):
    if "youtube.com" in url:
        return "YouTube"
    elif "blog" in url:
        return "Blog"
    elif "news" in url:
        return "News"
    else:
        return "Other"

# Create an enhanced heatmap of collected links
def create_enhanced_heatmap(links, output_dir):
    plt.figure(figsize=(12, 8))
    domains = [urlparse(link).netloc for link in links]
    domain_counts = {domain: domains.count(domain) for domain in set(domains)}
    heatmap_data = pd.DataFrame(list(domain_counts.items()), columns=['Domain', 'Count'])
    heatmap_data_pivot = heatmap_data.pivot_table(index='Domain', values='Count', aggfunc='sum')
    ax = sns.heatmap(heatmap_data_pivot, cmap='coolwarm', annot=True, fmt='d', linewidths=.5)
    ax.set_title('Heatmap of Collected Links', fontsize=20)
    ax.set_xlabel('Count of Links', fontsize=14)
    ax.set_ylabel('Domain', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'enhanced_heatmap.png'))
    plt.close()
    logging.info("Enhanced heatmap generated.")

# Create a real-time network graph with detailed information
def create_real_time_network_graph(graph_data, output_dir):
    G = nx.DiGraph()
    
    for node in graph_data["nodes"]:
        G.add_node(node['url'], **node)

    for edge in graph_data["edges"]:
        if edge[0] in G and edge[1] in G:
            G.add_edge(edge[0], edge[1])

    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=700, node_color='lightblue', font_size=10, font_weight='bold', edge_color='gray')
    plt.title('Network Graph of Crawled Links')
    plt.savefig(os.path.join(output_dir, 'network_graph.png'))
    plt.close()
    logging.info("Network graph generated.")

# Main crawling function
def crawl(settings):
    graph_data = {"nodes": [], "edges": []}
    visited = set()
    urls_to_visit = settings['urls_to_visit']

    while urls_to_visit:
        user_agent = get_random_user_agent(settings['user_agents'])
        with ThreadPoolExecutor(max_workers=settings['connections']) as executor:
            futures = {executor.submit(fetch_url, url, user_agent, graph_data, visited): url for url in urls_to_visit}
            urls_to_visit = []
            for future in futures:
                new_links = future.result()
                urls_to_visit.extend(new_links)
                # Rate limit after processing each batch
                rate_limiter(1)

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
        print(f"7. Set user agents (Current: {len(settings['user_agents'])} agents)")
        print(f"8. Toggle resume crawl (Current: {'On' if settings['resume'] else 'Off'})")
        print(f"9. Select crawl method (Current: Method {settings['crawl_method']})")
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
            user_agents = input("Enter user agents (comma-separated): ")
            settings['user_agents'] = user_agents.split(",")
        elif choice == "8":
            settings['resume'] = not settings['resume']
        elif choice == "9":
            settings['crawl_method'] = int(input("Enter crawl method (1 or 2): "))
        elif choice == "10":
            return settings
        elif choice == "11":
            exit()

# Main function to run the crawler
def main():
    settings = {
        'url_file': 'urls.txt',
        'connections': 5,
        'timeout': 10,
        'search_links': True,
        'output_dir': './output',
        'depth': 2,
        'user_agents': ['Mozilla/5.0', 'Chrome/91.0', 'Safari/537.36'],
        'resume': False,
        'crawl_method': 1,  # Default method 1
        'urls_to_visit': []  # Start with an empty list
    }

    # Load URLs from the specified file
    try:
        with open(settings['url_file'], 'r') as file:
            settings['urls_to_visit'] = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logging.error(f"File {settings['url_file']} not found. Please ensure it exists.")
        return  # Exit if the file is not found

    settings = display_general_menu(settings)
    ensure_files_and_directories(settings)
    setup_logging(settings['output_dir'])
    
    # Start crawling process
    crawl(settings)
    create_enhanced_heatmap([node['url'] for node in settings['urls_to_visit']], settings['output_dir'])
    create_real_time_network_graph(settings['output_dir'])
    logging.info("Web crawling completed.")


if __name__ == '__main__':
    install_dependencies()
    main()

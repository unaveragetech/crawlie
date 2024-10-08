import os
import logging
import math
import random
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import pandas as pd
from io import BytesIO
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
import threading
import time

# Function to ensure required libraries are installed
def install_dependencies():
    try:
        import requests
        import bs4
        import matplotlib
        import seaborn
        import networkx
        import pandas
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

# Menu system for setting options, including crawl method selection
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
def create_real_time_network_graph(link_pairs, output_dir, settings):
    G = nx.DiGraph()
    graph_data = {"nodes": [], "edges": []}

    def update_network_graph():
        fig, ax = plt.subplots(figsize=(20, 20))
        logging.info(f"Graph data nodes: {graph_data['nodes']}")
        
        G = nx.DiGraph()
        for node in graph_data['nodes']:
            G.add_node(node['url'], **node)
        for edge in graph_data['edges']:
            if edge[0] in G and edge[1] in G:
                G.add_edge(edge[0], edge[1])

        node_colors = []
        node_sizes = []
        labels = {}
        
        for node, data in G.nodes(data=True):
            node_type = data.get('type', 'Unknown')
            response_time = data.get('response_time', 0)
            domain = data.get('domain', 'Unknown')
            node_colors.append("lightblue" if node_type == "YouTube" else "lightgreen")
            node_sizes.append(300 + response_time * 500)
            labels[node] = f"{domain}\n{response_time:.2f}s"

        if len(G.nodes()) == 0:
            logging.warning("No valid nodes to display in the network graph.")
            return

        pos = nx.spring_layout(G)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.7)
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray', arrows=True, arrowsize=10, width=0.5, alpha=0.5)
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=8)

        ax.set_title('Network Graph of Crawled Links', fontsize=24, fontweight='bold')
        ax.axis('off')

        response_times = [data.get('response_time', 0) for _, data in G.nodes(data=True)]
        if response_times:
            sm = plt.cm.ScalarMappable(cmap='coolwarm', norm=plt.Normalize(vmin=min(response_times), vmax=max(response_times)))
            sm.set_array([])
            cbar = fig.colorbar(sm, ax=ax)
            cbar.set_label('Response Time (seconds)', fontsize=12)

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'network_graph.png'), dpi=300, bbox_inches='tight')
        plt.close(fig)

    # Crawling Method 1: Crawl based on keywords in the URL (from script 1)
    def crawl_and_update_method_1():
        urls_to_visit = settings['urls_to_visit']
        user_agent = random.choice(settings['user_agents'])
        visited = set()

        while urls_to_visit:
            new_urls_to_visit = []
            for url in urls_to_visit:
                if url in visited:
                    continue
                try:
                    start_time = time.time()
                    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=settings['timeout'])
                    response.raise_for_status()
                    end_time = time.time()
                    response_time = end_time - start_time

                    # Classify page type
                    if any(keyword in url for keyword in ['youtube', 'video']):
                        page_type = 'YouTube'
                    elif any(keyword in url for keyword in ['blog', 'article']):
                        page_type = 'Blog'
                    else:
                        page_type = 'Other'

                    domain = urlparse(url).netloc
                    graph_data["nodes"].append({
                        "url": url,
                        "type": page_type,
                        "response_time": response_time,
                        "domain": domain
                    })

                    # Extract links from the page
                    new_links = search_links(response.text, url)
                    for link in new_links:
                        graph_data["edges"].append((url, link))
                        new_urls_to_visit.append(link)

                    visited.add(url)
                    update_network_graph()

                except requests.RequestException as e:
                    logging.error(f"Error fetching {url}: {e}")

            urls_to_visit = new_urls_to_visit
            if not urls_to_visit:
                break

    # Crawling Method 2: Follow all links recursively, similar to script 2
    def crawl_and_update_method_2():
        urls_to_visit = settings['urls_to_visit']
        user_agent = random.choice(settings['user_agents'])
        visited = set()

        for depth in range(settings['depth']):
            new_urls_to_visit = []
            for url in urls_to_visit:
                if url in visited:
                    continue
                try:
                    start_time = time.time()
                    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=settings['timeout'])
                    response.raise_for_status()
                    end_time = time.time()
                    response_time = end_time - start_time
                    content = response.text
                    page_type = classify_page_type(url)
                    domain = urlparse(url).netloc

                    graph_data["nodes"].append({
                        "url": url,
                        "type": page_type,
                        "response_time": response_time,
                        "domain": domain
                    })

                    new_links = search_links(content, url)
                    for link in new_links:
                        graph_data["edges"].append((url, link))
                        new_urls_to_visit.append(link)

                    visited.add(url)
                    update_network_graph()

                except requests.RequestException as e:
                    logging.error(f"Error fetching {url}: {e}")

            urls_to_visit = new_urls_to_visit
            if not urls_to_visit:
                break

    def crawl_and_update(settings):
        if settings['crawl_method'] == 1:
            crawl_and_update_method_1()
        elif settings['crawl_method'] == 2:
            crawl_and_update_method_2()

# Main function to run the crawler
def main():
    settings = {
        'url_file': 'urls.txt',
        'connections': 5,
        'timeout': 10,
        'search_links': True,
        'output_dir': './output',
        'depth': 2,
        'user_agents': ['Mozilla/5.0'],
        'resume': False,
        'crawl_method': 1,  # Default method 1
        'urls_to_visit': ['http://example.com']
    }

    settings = display_general_menu(settings)

    ensure_files_and_directories(settings)
    setup_logging(settings['output_dir'])
    
    # Start crawling process
    crawl_and_update(settings)
    create_enhanced_heatmap(settings['urls_to_visit'], settings['output_dir'])
    logging.info("Web crawling completed.")

if __name__ == '__main__':
    install_dependencies()
    main()

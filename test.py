import os
import logging
import math
import random
import matplotlib.pyplot as plt
import seaborn as sns # For enhanced heatmap visualization
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
        print("9. Start crawl")
        print("10. Exit")
        choice = input("Enter your choice (1-10): ")
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
            return settings
        elif choice == "10":
            exit()

# Function to search for links in the HTML content using BeautifulSoup
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

# Function to create an enhanced heatmap of collected links
def create_enhanced_heatmap(links, output_dir):
    plt.figure(figsize=(12, 8))
    domains = [urlparse(link).netloc for link in links]
    domain_counts = {domain: domains.count(domain) for domain in set(domains)}
    # Create a DataFrame for better handling
    heatmap_data = pd.DataFrame(list(domain_counts.items()), columns=['Domain', 'Count'])
    # Using pivot_table to create heatmap data
    heatmap_data_pivot = heatmap_data.pivot_table(index='Domain', values='Count', aggfunc='sum')
    # Using Seaborn to create a more aesthetically pleasing heatmap
    ax = sns.heatmap(heatmap_data_pivot, cmap='coolwarm', annot=True, fmt='d', linewidths=.5)
    ax.set_title('Heatmap of Collected Links', fontsize=20)
    ax.set_xlabel('Count of Links', fontsize=14)
    ax.set_ylabel('Domain', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    # Save the heatmap
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'enhanced_heatmap.png'))
    plt.close()
    logging.info("Enhanced heatmap generated.")

# Function to create a real-time network graph with detailed information
def create_real_time_network_graph(link_pairs, output_dir, settings):
    G = nx.DiGraph()
    # Track nodes and edges dynamically
    graph_data = {"nodes": [], "edges": []}

    def update_network_graph():
        fig, ax = plt.subplots(figsize=(20, 20))
        logging.info(f"Graph data nodes: {graph_data['nodes']}")
        
        G = nx.DiGraph()  # Create a new graph object each time
        
        # Add nodes and edges to the graph
        for node in graph_data['nodes']:
            G.add_node(node['url'], **node)
        for edge in graph_data['edges']:
            if edge[0] in G and edge[1] in G:  # Only add edges between existing nodes
                G.add_edge(edge[0], edge[1])
        
        node_colors = []
        node_sizes = []
        labels = {}
        
        for node, data in G.nodes(data=True):
            node_type = data.get('type', 'Unknown')
            response_time = data.get('response_time', 0)
            domain = data.get('domain', 'Unknown')
            
            node_colors.append("lightblue" if node_type == "YouTube" else "lightgreen")
            node_sizes.append(300 + response_time * 500)  # Increase size difference
            labels[node] = f"{domain}\n{response_time:.2f}s"
        
        logging.info(f"Node sizes length: {len(node_sizes)}, Node colors length: {len(node_colors)}, Graph nodes length: {len(G.nodes())}")
        
        if len(G.nodes()) == 0:
            logging.warning("No valid nodes to display in the network graph.")
            return
        
        # Custom layout function
        def custom_layout(G, center=(0, 0), scale=1):
            pos = {}
            nodes = list(G.nodes(data=True))
            for i, (node, data) in enumerate(nodes):
                angle = 2 * math.pi * i / len(nodes)
                radius = scale * (1 + data.get('response_time', 0))
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                pos[node] = (x, y)
            return pos
        
        # Generate layout
        pos = custom_layout(G, scale=10)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.7)
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray', arrows=True, arrowsize=10, width=0.5, alpha=0.5)
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=8)
        
        ax.set_title('Enhanced Network Graph of Crawled Links', fontsize=24, fontweight='bold')
        ax.axis('off')
        
        # Add a colorbar legend based on response time
        response_times = [data.get('response_time', 0) for _, data in G.nodes(data=True)]
        if response_times:
            sm = plt.cm.ScalarMappable(cmap='coolwarm', norm=plt.Normalize(vmin=min(response_times), vmax=max(response_times)))
            sm.set_array([])
            cbar = fig.colorbar(sm, ax=ax)
            cbar.set_label('Response Time (seconds)', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'network_graph.png'), dpi=300, bbox_inches='tight')
        plt.close(fig)


    def crawl_and_update():
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

                    # Add node data with response time
                    graph_data["nodes"].append({
                        "url": url,
                        "type": page_type,
                        "response_time": response_time,
                        "domain": domain
                    })

                    # Search for links and update edges
                    new_links = search_links(content, url)
                    for link in new_links:
                        graph_data["edges"].append((url, link))
                        new_urls_to_visit.append(link)

                    visited.add(url)
                    # Update the graph in real-time
                    update_network_graph()
                except requests.RequestException as e:
                    logging.error(f"Error fetching {url}: {e}")

            urls_to_visit = new_urls_to_visit
            if not urls_to_visit:
                break

    # Start the crawling and updating in a separate thread
    crawl_thread = threading.Thread(target=crawl_and_update)
    crawl_thread.start()
    crawl_thread.join()  # Wait for the crawl to complete

# Main crawl function
def perform_crawl(settings):
    # Generate and maintain real-time network graph
    links_collected = []
    link_pairs = []
    with open(settings['url_file'], 'r') as f:
        settings['urls_to_visit'] = [line.strip() for line in f if line.strip()]
    create_real_time_network_graph(link_pairs, settings['output_dir'], settings)
    return links_collected

# Main function to kickstart everything
def main():
    install_dependencies()
    settings = {
        'url_file': 'urls.txt', # Default URL file
        'connections': 10,
        'timeout': 5,
        'search_links': True,
        'output_dir': 'output',
        'depth': 2,
        'user_agents': [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 Edge/17.17134"
        ],
        'resume': False,
        'urls_to_visit': []
    }
    setup_logging(settings['output_dir'])
    ensure_files_and_directories(settings)
    settings = display_general_menu(settings)
    perform_crawl(settings)

if __name__ == "__main__":
    main()
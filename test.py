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
from tqdm import tqdm
import json
import concurrent.futures
from collections import Counter
import csv

# Constants
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
]

def install_dependencies():
    try:
        import requests
        import bs4
        import matplotlib
        import seaborn
        import networkx
        import pandas
        import tqdm
    except ImportError:
        print("Required libraries are missing. Install via pip.")

def setup_logging(output_dir):
    logging.basicConfig(
        filename=os.path.join(output_dir, 'crawler.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Logging initialized.")

def ensure_files_and_directories(settings):
    if not os.path.exists(settings['output_dir']):
        os.makedirs(settings['output_dir'])

def load_settings():
    if os.path.exists('settings.json'):
        with open('settings.json', 'r') as f:
            return json.load(f)
    return {
        'url_file': 'urls.txt',
        'output_dir': 'crawler_output',
        'connections': 10,
        'timeout': 5,
        'search_links': True,
        'depth': 3,
        'user_agents': USER_AGENTS,
        'resume': False,
        'threads': 4,
        'keyword_search': '',
        'urls_to_visit': []
    }

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

def display_general_menu(settings):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== Web Crawler Settings Menu ===")
        print(f"1. Set URL file (Current: {settings['url_file']})")
        print(f"2. Set number of connections (Current: {settings['connections']})")
        print(f"3. Set timeout (Current: {settings['timeout']} seconds)")
        print(f"4. Toggle search links (Current: {'On' if settings['search_links'] else 'Off'})")
        print(f"5. Set output directory (Current: {settings['output_dir']})")
        print(f"6. Set crawl depth (Current: {settings['depth']})")
        print(f"7. Set user agents (Current: {len(settings['user_agents'])} agents)")
        print(f"8. Toggle resume crawl (Current: {'On' if settings['resume'] else 'Off'})")
        print(f"9. Set number of threads (Current: {settings['threads']})")
        print(f"10. Set keyword search (Current: {settings['keyword_search']})")
        print("11. Start crawl")
        print("12. Save settings")
        print("13. Exit")

        choice = input("Enter your choice (1-13): ")

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
            settings['user_agents'] = [ua.strip() for ua in user_agents.split(",")]
        elif choice == "8":
            settings['resume'] = not settings['resume']
        elif choice == "9":
            settings['threads'] = int(input("Enter number of threads: "))
        elif choice == "10":
            settings['keyword_search'] = input("Enter keyword to search for: ")
        elif choice == "11":
            save_settings(settings)
            return settings
        elif choice == "12":
            save_settings(settings)
            print("Settings saved.")
        elif choice == "13":
            save_settings(settings)
            exit()
        else:
            print("Invalid choice. Please try again.")

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

def classify_page_type(url):
    if "youtube.com" in url:
        return "YouTube"
    elif "blog" in url:
        return "Blog"
    elif "news" in url:
        return "News"
    else:
        return "Other"

def create_enhanced_heatmap(graph_data, output_dir):
    plt.figure(figsize=(16, 12))
    domains = [urlparse(node['url']).netloc for node in graph_data['nodes']]
    domain_counts = Counter(domains)
    
    heatmap_data = pd.DataFrame(list(domain_counts.items()), columns=['Domain', 'Count'])
    heatmap_data = heatmap_data.sort_values('Count', ascending=False).head(30)  # Top 30 domains
    
    ax = sns.barplot(x='Count', y='Domain', data=heatmap_data, hue='Domain', palette='viridis', legend=False)
    ax.set_title('Top 30 Domains Crawled', fontsize=20)
    ax.set_xlabel('Number of Pages', fontsize=14)
    ax.set_ylabel('Domain', fontsize=14)
    
    for i, v in enumerate(heatmap_data['Count']):
        ax.text(v + 0.1, i, str(v), va='center')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'domain_heatmap.png'), dpi=300)
    plt.close()
    logging.info("Enhanced domain heatmap generated.")

def create_detailed_network_graph(graph_data, output_dir):
    G = nx.DiGraph()
    for node in graph_data['nodes']:
        G.add_node(node['url'], **node)
    for edge in graph_data['edges']:
        if edge[0] in G and edge[1] in G:
            G.add_edge(edge[0], edge[1])

    if len(G.nodes()) == 0:
        logging.warning("No nodes to display in the network graph.")
        return

    fig, ax = plt.subplots(figsize=(24, 18))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    node_sizes = [300 + node['response_time'] * 500 for node in G.nodes.values()]
    
    max_depth = max((node['depth'] for node in G.nodes.values()), default=1)
    if max_depth == 0:
        max_depth = 1  # Avoid division by zero
    node_colors = [plt.cm.viridis(node['depth'] / max_depth) for node in G.nodes.values()]
    
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.7)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray', arrows=True, arrowsize=10, width=0.5, alpha=0.5)
    
    labels = {node: f"{urlparse(node).netloc}\n{data['response_time']:.2f}s" for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=6)
    
    ax.set_title('Detailed Network Graph of Crawled Links', fontsize=24, fontweight='bold')
    ax.axis('off')
    
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin=0, vmax=max_depth))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label('Crawl Depth', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'detailed_network_graph.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    logging.info("Detailed network graph generated.")

def crawl_url(url, depth, thread_id, thread_status, settings, visited, new_urls_to_visit, graph_data):
    if url in visited:
        return
    try:
        headers = {"User-Agent": random.choice(settings['user_agents'])}
        start_time = time.time()
        thread_status[thread_id] = f"Crawling: {url}"
        response = requests.get(url, headers=headers, timeout=settings['timeout'])
        response.raise_for_status()
        end_time = time.time()
        response_time = end_time - start_time
        content = response.text
        page_type = classify_page_type(url)
        domain = urlparse(url).netloc

        graph_data['nodes'].append({
            'url': url,
            'type': page_type,
            'domain': domain,
            'response_time': response_time,
            'depth': depth
        })

        logging.info(f"Processing URL: {url} [{page_type}] with response time: {response_time:.2f}s")

        if settings['keyword_search'] and settings['keyword_search'].lower() in content.lower():
            logging.info(f"Keyword '{settings['keyword_search']}' found in {url}")

        if settings['search_links'] and depth < settings['depth']:
            links = search_links(content, url)
            for link in links:
                if link not in visited:
                    graph_data['edges'].append((url, link))
                    new_urls_to_visit.append((link, depth + 1))

        visited.add(url)

    except Exception as e:
        logging.error(f"Failed to crawl URL {url}: {e}")
    finally:
        thread_status[thread_id] = "Idle"

def crawl_and_update(settings, pbar):
    visited = set()
    urls_to_visit = [(url, 0) for url in settings['urls_to_visit']]
    new_urls_to_visit = []
    graph_data = {"nodes": [], "edges": []}
    thread_status = {}

    def display_thread_status():
        while urls_to_visit or new_urls_to_visit:
            os.system('cls' if os.name == 'nt' else 'clear')
            pbar.display()
            print("\nThread Status:")
            for thread_id, status in thread_status.items():
                print(f"{thread_id}: {status}")
            time.sleep(0.5)

    status_thread = threading.Thread(target=display_thread_status)
    status_thread.daemon = True
    status_thread.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=settings['threads']) as executor:
        while urls_to_visit or new_urls_to_visit:
            if not urls_to_visit:
                urls_to_visit = new_urls_to_visit
                new_urls_to_visit = []

            futures = []
            for i, (url, depth) in enumerate(urls_to_visit[:settings['connections']]):
                thread_id = f"Thread-{i+1}"
                thread_status[thread_id] = "Starting"
                futures.append(executor.submit(crawl_url, url, depth, thread_id, thread_status, settings, visited, new_urls_to_visit, graph_data))

            concurrent.futures.wait(futures)
            urls_to_visit = urls_to_visit[settings['connections']:]
            pbar.update(len(futures))

    return visited, graph_data

def export_data(visited, graph_data, output_dir):
    # Export to CSV
    with open(os.path.join(output_dir, 'crawled_data.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Type', 'Domain', 'Response Time', 'Depth'])
        for node in graph_data['nodes']:
            writer.writerow([node['url'], node['type'], node['domain'], node['response_time'], node['depth']])

    # Export to JSON
    with open(os.path.join(output_dir, 'crawled_data.json'), 'w') as f:
        json.dump(graph_data, f, indent=4)

def main():
    settings = load_settings()
    settings = display_general_menu(settings)

    with open(settings['url_file'], 'r') as f:
        settings['urls_to_visit'] = [line.strip() for line in f]

    ensure_files_and_directories(settings)
    setup_logging(settings['output_dir'])
    
    total_urls = len(settings['urls_to_visit']) * settings['depth']
    with tqdm(total=total_urls, desc="Crawling", unit="page") as pbar:
        visited, graph_data = crawl_and_update(settings, pbar)

    create_enhanced_heatmap(graph_data, settings['output_dir'])
    create_detailed_network_graph(graph_data, settings['output_dir'])
    export_data(visited, graph_data, settings['output_dir'])
    
    print(f"Crawl completed. Visited {len(visited)} pages.")
    print(f"Results saved in {settings['output_dir']}")

if __name__ == "__main__":
    install_dependencies()
    main()
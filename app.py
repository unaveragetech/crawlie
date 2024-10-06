#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pycurl
import argparse
import subprocess
import os
from urllib.parse import urljoin, urlparse
import logging
import json
import matplotlib.pyplot as plt
import collections
import random
import time
import pickle
import networkx as nx
import plotly.graph_objects as go
from urllib.robotparser import RobotFileParser

# Function to install dependencies
def install_dependencies():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pycurl", "matplotlib", "networkx", "plotly"])
    except Exception as e:
        print(f"Failed to install dependencies: {e}")
        sys.exit(1)

# Search for associated links on the page
def search_links(content, base_url):
    links = []
    for line in content.splitlines():
        if "href=" in line:
            start = line.find("href=") + len("href=") + 1
            end = line.find('"', start)
            url = line[start:end]
            if not url.startswith("http"):
                url = urljoin(base_url, url)
            links.append(url)
    return links

# Setup logging to file and console
def setup_logging(output_dir):
    log_file = os.path.join(output_dir, "log.txt")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
    logging.info("Logging initialized.")

# Create interactive heatmap using Plotly
def create_heatmap(link_data, output_dir):
    domain_counter = collections.Counter(link_data)
    domains, counts = zip(*domain_counter.items())
    
    fig = go.Figure(data=[go.Bar(x=counts, y=domains, orientation='h')])
    fig.update_layout(title="Interactive Heatmap of Link Frequencies",
                      xaxis_title="Number of Links",
                      yaxis_title="Domain")
    
    heatmap_path = os.path.join(output_dir, "interactive_heatmap.html")
    fig.write_html(heatmap_path)
    logging.info(f"Interactive heatmap saved at {heatmap_path}")

# Create network graph
def create_network_graph(links, output_dir):
    G = nx.Graph()
    for source, target in links:
        G.add_edge(source, target)
    
    pos = nx.spring_layout(G)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

    node_x, node_y = [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', marker=dict(size=10, color='#00b4d9'))

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(showlegend=False, hovermode='closest',
                                     margin=dict(b=0,l=0,r=0,t=0)))
    
    network_path = os.path.join(output_dir, "network_graph.html")
    fig.write_html(network_path)
    logging.info(f"Network graph saved at {network_path}")

# Function to check robots.txt and implement rate limiting
def respect_robots_txt(url, user_agent):
    rp = RobotFileParser()
    rp.set_url(urljoin(url, "/robots.txt"))
    rp.read()
    
    if not rp.can_fetch(user_agent, url):
        logging.warning(f"Robots.txt disallows fetching {url}")
        return False
    
    crawl_delay = rp.crawl_delay(user_agent)
    if crawl_delay:
        time.sleep(crawl_delay)
    else:
        time.sleep(1)  # Default delay
    
    return True

# Function for the menu system
def display_menu():
    settings = {
        "url_file": "",
        "connections": 10,
        "timeout": 300,
        "search_links": False,
        "output_dir": "output",
        "depth": 1,
        "headers": {},
        "user_agents": ["Mozilla/5.0"],
        "resume": False
    }

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
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

        if choice == '1':
            settings['url_file'] = input("Enter the URL file path: ")
        elif choice == '2':
            settings['connections'] = int(input("Enter the number of connections: "))
        elif choice == '3':
            settings['timeout'] = int(input("Enter the timeout in seconds: "))
        elif choice == '4':
            settings['search_links'] = not settings['search_links']
        elif choice == '5':
            settings['output_dir'] = input("Enter the output directory: ")
        elif choice == '6':
            settings['depth'] = int(input("Enter the crawl depth: "))
        elif choice == '7':
            header_input = input("Enter custom headers as a JSON string (e.g., {\"User-Agent\": \"MyBot\"}): ")
            settings['headers'] = json.loads(header_input)
        elif choice == '8':
            agents = input("Enter user agents separated by commas: ")
            settings['user_agents'] = [agent.strip() for agent in agents.split(',')]
        elif choice == '9':
            settings['resume'] = not settings['resume']
        elif choice == '10':
            return settings
        elif choice == '11':
            print("Exiting...")
            sys.exit(0)
        else:
            input("Invalid choice. Press Enter to continue...")

# Main function
def main():
    install_dependencies()
    settings = display_menu()

    if not os.path.exists(settings['output_dir']):
        os.makedirs(settings['output_dir'])
    setup_logging(settings['output_dir'])

    # Load or initialize crawl state
    state_file = os.path.join(settings['output_dir'], "crawl_state.pkl")
    if settings['resume'] and os.path.exists(state_file):
        with open(state_file, "rb") as f:
            crawl_state = pickle.load(f)
        logging.info("Resuming previous crawl")
    else:
        crawl_state = {"processed_urls": set(), "queue": []}

    try:
        if settings['url_file'] == "-":
            urls = sys.stdin.readlines()
        else:
            with open(settings['url_file'], 'r') as f:
                urls = f.readlines()
    except Exception as e:
        logging.error(f"Error reading URL file: {e}")
        sys.exit(1)

    # Initialize queue if starting fresh
    if not crawl_state["queue"]:
        for url in urls:
            url = url.strip()
            if url and not url.startswith("#"):
                crawl_state["queue"].append((url, 0))  # (url, depth)

    num_conn = min(settings['connections'], len(crawl_state["queue"]))
    logging.info(f"PycURL {pycurl.version} (compiled against {pycurl.COMPILE_LIBCURL_VERSION_NUM})")
    logging.info(f"----- Processing {len(crawl_state['queue'])} URLs using {num_conn} connections -----")

    m = pycurl.CurlMulti()
    m.handles = []
    for _ in range(num_conn):
        c = pycurl.Curl()
        c.fp = None
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        c.setopt(pycurl.CONNECTTIMEOUT, 30)
        c.setopt(pycurl.TIMEOUT, settings['timeout'])
        c.setopt(pycurl.NOSIGNAL, 1)
        m.handles.append(c)

    freelist = m.handles[:]
    num_processed = 0
    all_links = []
    
    while crawl_state["queue"]:
        while crawl_state["queue"] and freelist:
            url, depth = crawl_state["queue"].pop(0)
            if url in crawl_state["processed_urls"]:
                continue
            
            c = freelist.pop()
            user_agent = random.choice(settings['user_agents'])
            
            if not respect_robots_txt(url, user_agent):
                freelist.append(c)
                continue
            
            c.fp = open(os.path.join(settings['output_dir'], f"doc_{num_processed:03d}.dat"), "wb")
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.WRITEDATA, c.fp)
            c.setopt(pycurl.USERAGENT, user_agent)
            for key, value in settings['headers'].items():
                c.setopt(pycurl.HTTPHEADER, [f"{key}: {value}"])
            m.add_handle(c)
            c.url = url
            c.depth = depth

        while True:
            ret, num_handles = m.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

        while True:
            num_q, ok_list, err_list = m.info_read()
            for c in ok_list:
                c.fp.close()
                c.fp = None
                m.remove_handle(c)
                crawl_state["processed_urls"].add(c.url)
                logging.info(f"Success: {c.url}")
                
                if settings['search_links'] and c.depth < settings['depth']:
                    with open(c.fp.name, 'r') as f:
                        content = f.read()
                    links = search_links(content, c.url)
                    for link in links:
                        if link not in crawl_state["processed_urls"]:
                            crawl_state["queue"].append((link, c.depth + 1))
                            all_links.append((c.url, link))
                
                freelist.append(c)
            
            for c, errno, errmsg in err_list:
                c.fp.close()
                c.fp = None
                m.remove_handle(c)
                crawl_state["processed_urls"].add(c.url)
                logging.error(f"Failed: {c.url}, {errno}, {errmsg}")
                freelist.append(c)
            
            num_processed += len(ok_list) + len(err_list)
            if num_q == 0:
                break
        
        m.select(1.0)
        
        # Save state periodically
        if num_processed % 10 == 0:
            with open(state_file, "wb") as f:
                pickle.dump(crawl_state, f)

    # Generate visualizations
    if all_links:
        domains = [urlparse(link[1]).netloc for link in all_links]
        create_heatmap(domains, settings['output_dir'])
        create_network_graph(all_links, settings['output_dir'])

    # Cleanup
    for c in m.handles:
        if c.fp is not None:
            c.fp.close()
        c.close()
    m.close()

    # Final state save
    with open(state_file, "wb") as f:
        pickle.dump(crawl_state, f)

if __name__ == "__main__":
    main()

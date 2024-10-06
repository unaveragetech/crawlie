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
from bs4 import BeautifulSoup  # Added for better HTML parsing


# Function to install dependencies
def install_dependencies():
    try:
        # It's recommended to handle dependencies outside runtime
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pycurl", "matplotlib", "networkx", "plotly", "beautifulsoup4", "lxml"])
    except Exception as e:
        print(f"Failed to install dependencies: {e}")
        sys.exit(1)


# Search for associated links on the page using BeautifulSoup
def search_links(content, base_url):
    links = []
    try:
        soup = BeautifulSoup(content, 'lxml')
        for link in soup.find_all('a', href=True):
            url = link['href']
            if not url.startswith("http"):
                url = urljoin(base_url, url)
            links.append(url)
    except Exception as e:
        logging.error(f"Error parsing HTML: {e}")
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
    domains, counts = zip(*domain_counter.items()) if domain_counter else ([], [])

    if domains and counts:
        fig = go.Figure(data=[go.Bar(x=counts, y=domains, orientation='h')])
        fig.update_layout(title="Interactive Heatmap of Link Frequencies",
                          xaxis_title="Number of Links",
                          yaxis_title="Domain")
    
        heatmap_path = os.path.join(output_dir, "interactive_heatmap.html")
        fig.write_html(heatmap_path)
        logging.info(f"Interactive heatmap saved at {heatmap_path}")
    else:
        logging.info("No data available to generate heatmap.")


# Create network graph
def create_network_graph(links, output_dir):
    if not links:
        logging.info("No links to generate network graph.")
        return

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
                                     margin=dict(b=0, l=0, r=0, t=0)))

    network_path = os.path.join(output_dir, "network_graph.html")
    fig.write_html(network_path)
    logging.info(f"Network graph saved at {network_path}")


# Function to check robots.txt and implement rate limiting
def respect_robots_txt(url, user_agent):
    rp = RobotFileParser()
    robots_url = urljoin(url, "/robots.txt")

    try:
        rp.set_url(robots_url)
        rp.read()

        if not rp.can_fetch(user_agent, url):
            logging.warning(f"Robots.txt disallows fetching {url}")
            return False

        crawl_delay = rp.crawl_delay(user_agent)
        if crawl_delay:
            time.sleep(crawl_delay)
        else:
            time.sleep(1)  # Default delay
    except Exception as e:
        logging.error(f"Error reading robots.txt at {robots_url}: {e}")
        time.sleep(1)  # Default to 1-second delay if error
    return True


# Function for the menu system with input validation
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

        try:
            if choice == '1':
                settings['url_file'] = input("Enter the URL file path: ").strip()
            elif choice == '2':
                settings['connections'] = max(1, int(input("Enter the number of connections (>=1): ").strip()))
            elif choice == '3':
                settings['timeout'] = max(1, int(input("Enter the timeout in seconds (>=1): ").strip()))
            elif choice == '4':
                settings['search_links'] = not settings['search_links']
            elif choice == '5':
                settings['output_dir'] = input("Enter the output directory: ").strip()
            elif choice == '6':
                settings['depth'] = max(1, int(input("Enter the crawl depth (>=1): ").strip()))
            elif choice == '7':
                header_input = input("Enter custom headers as a JSON string (e.g., {\"User-Agent\": \"MyBot\"}): ").strip()
                settings['headers'] = json.loads(header_input)
            elif choice == '8':
                agents = input("Enter user agents separated by commas: ").strip()
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
        except ValueError:
            input("Invalid input. Press Enter to continue...")


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
    for i in range(num_conn):
        c = pycurl.Curl()
        m.handles.append(c)

    # Crawl logic with better error handling and state saving
    active_handles = 0
    while crawl_state["queue"]:
        while active_handles < num_conn and crawl_state["queue"]:
            url, depth = crawl_state["queue"].pop(0)
            if url in crawl_state["processed_urls"]:
                continue

            if not respect_robots_txt(url, settings['user_agents'][0]):
                continue

            c = m.handles[active_handles]
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.TIMEOUT, settings['timeout'])

            # Assign file to save the output
            output_file = os.path.join(settings['output_dir'], f"doc_{random.randint(1000, 9999)}.dat")
            try:
                c.fp = open(output_file, "wb")
                c.setopt(c.WRITEDATA, c.fp)
            except Exception as e:
                logging.error(f"Error opening file {output_file} for writing: {e}")
                continue

            c.url = url
            c.depth = depth
            c.output_file = output_file
            m.add_handle(c)
            active_handles += 1

        while True:
            ret, num_handles = m.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

        while True:
            num_q, ok_list, err_list = m.info_read()
            for c in ok_list:
                # Fetch links if required and add them to the queue
                if settings['search_links'] and c.depth < settings['depth']:
                    with open(c.output_file, "rb") as f:
                        content = f.read()
                    links = search_links(content, c.url)
                    for link in links:
                        crawl_state["queue"].append((link, c.depth + 1))

                crawl_state["processed_urls"].add(c.url)
                m.remove_handle(c)
                active_handles -= 1
                c.fp.close()

            for c, errno, errmsg in err_list:
                logging.error(f"Failed fetching {c.url}: {errmsg}")
                m.remove_handle(c)
                active_handles -= 1
                c.fp.close()

            if num_q == 0:
                break

    # Save the crawl state
    with open(state_file, "wb") as f:
        pickle.dump(crawl_state, f)

    # Generate visualizations if there are results
    create_heatmap([urlparse(url).netloc for url in crawl_state['processed_urls']], settings['output_dir'])
    create_network_graph([(urlparse(src).netloc, urlparse(tgt).netloc) for src, tgt in crawl_state['queue']], settings['output_dir'])


if __name__ == '__main__':
    main()

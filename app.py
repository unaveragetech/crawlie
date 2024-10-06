#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

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

# Function to install dependencies
def install_dependencies():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pycurl", "matplotlib"])
    except Exception as e:
        print(f"Failed to install dependencies: {e}")
        sys.exit(1)

# Advanced CLI for granular control
def parse_arguments():
    parser = argparse.ArgumentParser(description="Advanced URL Fetcher with PyCURL, logging, and heatmap generation")
    parser.add_argument("url_file", help="File containing the list of URLs to fetch")
    parser.add_argument("-c", "--connections", type=int, default=10, help="Number of concurrent connections (default: 10)")
    parser.add_argument("-t", "--timeout", type=int, default=300, help="Timeout for connections in seconds (default: 300)")
    parser.add_argument("-s", "--search-links", action="store_true", help="Enable searching for associated links on the pages")
    parser.add_argument("-o", "--output-dir", type=str, default="output", help="Directory to store fetched pages and logs")
    return parser.parse_args()

# Search for associated links on the page (simplified for demo purposes)
def search_links(content, base_url):
    # A simple pattern-based search for URLs within the page content
    links = []
    for line in content.splitlines():
        if "href=" in line:
            start = line.find("href=") + len("href=") + 1
            end = line.find('"', start)
            url = line[start:end]
            if not url.startswith("http"):
                url = urljoin(base_url, url)  # Convert relative URL to absolute
            links.append(url)
    return links

# Setup logging to file and console
def setup_logging(output_dir):
    log_file = os.path.join(output_dir, "log.txt")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
    logging.info("Logging initialized.")

# Create heatmap from link data
def create_heatmap(link_data, output_dir):
    # Count domain frequencies
    domain_counter = collections.Counter(link_data)
    
    # Plot heatmap
    domains, counts = zip(*domain_counter.items())
    plt.figure(figsize=(10, 8))
    plt.barh(domains, counts, color='skyblue')
    plt.xlabel("Number of Links")
    plt.ylabel("Domain")
    plt.title("Heatmap of Link Frequencies")
    plt.tight_layout()
    
    # Save heatmap
    heatmap_path = os.path.join(output_dir, "heatmap.png")
    plt.savefig(heatmap_path)
    logging.info(f"Heatmap saved at {heatmap_path}")

# Get args and set up
def main():
    install_dependencies()
    args = parse_arguments()

    # Create output directories
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    setup_logging(args.output_dir)

    try:
        if args.url_file == "-":
            urls = sys.stdin.readlines()
        else:
            with open(args.url_file, 'r') as f:
                urls = f.readlines()
    except Exception as e:
        logging.error(f"Error reading URL file: {e}")
        sys.exit(1)

    num_conn = args.connections
    timeout = args.timeout

    # Make a queue with (url, filename) tuples
    queue = []
    for url in urls:
        url = url.strip()
        if not url or url[0] == "#":
            continue
        filename = f"doc_{len(queue) + 1:03}.dat"
        queue.append((url, filename))

    # Check arguments
    assert queue, "No URLs given"
    num_urls = len(queue)
    num_conn = min(num_conn, num_urls)
    assert 1 <= num_conn <= 10000, "Invalid number of concurrent connections"
    logging.info(f"PycURL {pycurl.version} (compiled against {pycurl.COMPILE_LIBCURL_VERSION_NUM})")
    logging.info(f"----- Getting {num_urls} URLs using {num_conn} connections -----")

    # Pre-allocate a list of curl objects
    m = pycurl.CurlMulti()
    m.handles = []
    for _ in range(num_conn):
        c = pycurl.Curl()
        c.fp = None
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        c.setopt(pycurl.CONNECTTIMEOUT, 30)
        c.setopt(pycurl.TIMEOUT, timeout)
        c.setopt(pycurl.NOSIGNAL, 1)
        m.handles.append(c)

    # Main loop
    freelist = m.handles[:]
    num_processed = 0
    all_links = []
    
    while num_processed < num_urls:
        # If there is a URL to process and a free curl object, add to multi stack
        while queue and freelist:
            url, filename = queue.pop(0)
            c = freelist.pop()
            file_path = os.path.join(args.output_dir, filename)
            c.fp = open(file_path, "wb")
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.WRITEDATA, c.fp)
            m.add_handle(c)
            # Store some info
            c.filename = filename
            c.url = url
        # Run the internal curl state machine for the multi stack
        while True:
            ret, num_handles = m.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break
        # Check for curl objects which have terminated, and add them to the freelist
        while True:
            num_q, ok_list, err_list = m.info_read()
            for c in ok_list:
                c.fp.close()
                c.fp = None
                m.remove_handle(c)
                logging.info(f"Success: {c.filename}, {c.url}, {c.getinfo(pycurl.EFFECTIVE_URL)}")
                # Search for associated links if enabled
                if args.search_links:
                    with open(os.path.join(args.output_dir, c.filename), 'r') as f:
                        content = f.read()
                    links = search_links(content, c.url)
                    if links:
                        logging.info(f"Found associated links for {c.url}:")
                        for link in links:
                            logging.info(f" - {link}")
                            all_links.append(link)
                freelist.append(c)
            for c, errno, errmsg in err_list:
                c.fp.close()
                c.fp = None
                m.remove_handle(c)
                logging.error(f"Failed: {c.filename}, {c.url}, {errno}, errmsg}")
                freelist.append(c)
            num_processed += len(ok_list) + len(err_list)
            if num_q == 0:
                break
        m.select(1.0)

    # Generate heatmap based on the links discovered
    if args.search_links:
        domains = [urlparse(link).netloc for link in all_links]
        create_heatmap(domains, args.output_dir)

    # Cleanup
    for c in m.handles:
        if c.fp is not None:
            c.fp.close()
        c.close()
    m.close()

if __name__ == "__main__":
    main()

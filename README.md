

| **Setting**               | **Description**                                                                                                               | **Default** | **Example**                       | **Invalid Operations**                                          | **Input For**                               |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------------|-------------|-----------------------------------|----------------------------------------------------------------|--------------------------------------------|
| **URL File**              | The name of the text file containing the URLs to crawl. Each URL should be on a new line. This file is essential for the crawler to know where to start. | `urls.txt`  | `youtube_links.txt`               | File does not exist, file is empty, or contains invalid URLs   | Name of the file to be read (e.g., `urls.txt`) |
| **Number of Connections** | The maximum number of simultaneous connections the crawler can make when fetching pages. Increasing this number can speed up the crawl but may also lead to throttling or blocking by websites. | `10`        | `5` (for fewer simultaneous requests) | Negative numbers, non-integer values                           | Integer value representing max connections  |
| **Timeout**               | The maximum time in seconds that the crawler will wait for a server response before considering the request failed. This setting helps manage slow servers or unresponsive pages. | `40`        | `30` (if the server is slow to respond) | Negative numbers, non-integer values                           | Integer value representing timeout in seconds |
| **Search Links**          | A boolean flag that indicates whether the crawler should extract links from the crawled pages. If set to `On`, the crawler will look for and collect all links found on each page. | `On`        | `Off` (to disable link extraction) | Values other than `On` or `Off`                                | `On` or `Off` to toggle link extraction    |
| **Output Directory**      | The directory where the crawler will save its output files, including logs, heatmaps, and graphs. This helps in organizing the results of the crawl. | `output`    | `results` (to save in a different folder) | Invalid directory paths, paths to files instead of directories   | Path where output files will be saved      |
| **Crawl Depth**           | The maximum number of levels the crawler will traverse from the original URLs. A depth of `1` means it will only crawl the provided URLs, while `2` will crawl links found on those pages. | `3`         | `2` (to limit the crawl to 2 levels) | Negative numbers, non-integer values                           | Integer value representing max crawl depth  |
| **User Agents**           | A list of user agent strings that the crawler can use to simulate different browsers or devices when making requests. This can help avoid being blocked by websites that filter traffic based on user agent. | `3 agents`  | `["Mozilla/5.0 ... Chrome/58.0.3029.110", "Mozilla/5.0 ... Firefox/54.0"]` | Empty list, invalid user agent formats                           | Comma-separated list of user agents        |
| **Resume Crawl**          | A boolean flag that indicates whether the crawler should continue from where it left off in case of a previous interrupted run. If set to `On`, it will try to resume crawling from previously visited URLs. | `Off`       | `On` (to allow continuation of interrupted crawls) | Values other than `On` or `Off`                                | `On` or `Off` to toggle resume feature      |





### New Commands Overview

| Command                   | Description                                                 | Example                                                |
|---------------------------|-------------------------------------------------------------|--------------------------------------------------------|
| `--url`                   | The starting URL for the crawler.                          | `--url https://example.com`                           |
| `--percentage`            | Percentage of links to fetch (0-100).                      | `--percentage 50`                                     |
| `--exfiltrate`           | Track the longest path of unique links.                    | `--exfiltrate`                                        |
| `--depth`                 | Specify the depth of links to crawl (default is 1).        | `--depth 3`                                          |
| `--threads`               | Number of threads to use for fetching links (default is 1). | `--threads 5`                                        |
| `--output`                | Specify the output file for saving URLs (default is `urls.txt`). | `--output my_links.txt`                                |
| `--timeout`               | Timeout for requests in seconds (default is 5).            | `--timeout 10`                                       |
| `--log-level`             | Set the logging level (default is INFO).                   | `--log-level DEBUG`                                  |
| `--follow-redirects`     | Follow redirects when fetching links.                      | `--follow-redirects`                                  |
| `--user-agent`           | Specify a custom user agent string for requests.           | `--user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"` |

### Usage Examples
```
1. **Basic Crawl**:
   ```bash
   python viz.py --url https://example.com --percentage 50
   ```

2. **Crawl with Exfiltration**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --exfiltrate
   ```

3. **Crawl with Custom Depth**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --depth 2
   ```

4. **Crawl with Threads**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --threads 4
   ```

5. **Custom Output File**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --output my_links.txt
   ```

6. **Set Timeout**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --timeout 10
   ```

7. **Change Logging Level**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --log-level DEBUG
   ```

8. **Follow Redirects**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --follow-redirects
   ```

9. **Custom User Agent**:
   ```bash
   python crawler.py --url https://example.com --percentage 50 --user-agent "Mozilla/5.0"
   ```


import concurrent.futures
import requests
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Suppress only the InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# Function to create the list of URLs
def generate_urls(base_url, start, end):
    return [f"{base_url}{i}.xxx.net/instance_id" for i in range(start, end + 1)]

# Base URL format
base_url = ''

# Generate URLs
URLS = generate_urls(base_url, 1, 60)

def create_session_with_retries():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def load_url(url, timeout):
    """Perform a GET request to the given URL with a timeout using a session with retries."""
    session = create_session_with_retries()
    try:
        # Specify connection and read timeouts separately
        resp = session.get(url, timeout=(60, 120))
        return resp.text
    except requests.exceptions.RequestException as e:
        return str(e)

def save_response(data, index):
    """Save data to a file named index_n where n is the index."""
    filename = f'index_{index}.txt'
    with open(filename, 'w') as file:
        file.write(data)

# Use ThreadPoolExecutor to perform requests concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=len(URLS)) as executor:
    # Map URLs to Future tasks
    future_to_index = {executor.submit(load_url, url, 31): 1 + i for i, url in enumerate(URLS)}

    # As each future completes, save its result to a file
    for future in concurrent.futures.as_completed(future_to_index):
        index = future_to_index[future]
        try:
            response_text = future.result()
        except Exception as exc:
            response_text = str(exc)

        save_response(response_text, index)
        print(f'Response from {URLS[index-1]} saved to index_{index}.txt')


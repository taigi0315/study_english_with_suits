import requests
from bs4 import BeautifulSoup

def get_dialogue_only(text):
    # Remove anything that looks like [Stage direction] etc.
    lines = text.split("\n")
    dialogue = [line for line in lines if line.strip() and not line.strip().startswith('[')]
    return "\n".join(dialogue)

# URL for testing
url = "https://transcripts.foreverdreaming.org/viewtopic.php?t=11489"
print(f"--- Testing transcript download for URL: {url} ---\n")

# Step 1: Fetch HTML content
print("1. Fetching HTML content...")
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print(f"   Success! Status code: {response.status_code}\n")
except requests.exceptions.RequestException as e:
    print(f"   Failed to fetch URL: {e}")
    exit()

# Step 2: Parse HTML with BeautifulSoup
print("2. Parsing HTML...")
soup = BeautifulSoup(response.text, 'html.parser')
print("   HTML parsed successfully.\n")

# Step 3: Find the transcript container
print("3. Finding transcript container...")
print("   Searching for <div class='postbody'> or <div class='content'>")
post_element = soup.find('div', class_='postbody') or soup.find('div', class_='content')

if not post_element:
    print("   Error: Could not find the transcript container element.")
    print("   Page source snippet (first 1000 chars):")
    print(response.text[:1000])
else:
    print("   Success! Found container element.\n")

    # Step 4: Extract text from the container
    print("4. Extracting text from container...")
    raw_text = post_element.get_text("\n")
    print("   Text extracted. First 500 characters of raw text:")
    print("   " + "-"*20)
    print(raw_text[:500].strip())
    print("   " + "-"*20 + "\n")

    # Step 5: Clean text to get only dialogue
    print("5. Cleaning text to get dialogue...")
    dialogue_text = get_dialogue_only(raw_text)
    print("   Dialogue extracted. First 500 characters of cleaned text:")
    print("   " + "-"*20)
    print(dialogue_text[:500].strip())
    print("   " + "-"*20 + "\n")

print("--- Test complete. ---")

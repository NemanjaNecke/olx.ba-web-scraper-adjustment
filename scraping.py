
import os
import time
import csv
import argparse
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


# ------------------------------
# OLX Scraping Functions
# ------------------------------

def extract_data(url, token):
    """
    Launches a headless browser with Playwright, loads the given URL,
    and uses BeautifulSoup to find all listing links.
    Then for each listing, calls the OLX API to get details (price and title).
    Returns a dict with lists of prices, titles, hrefs, and API logs.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"Error loading {url}: {e}")
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        hrefs = soup.select('a[href^="/artikal/"]')
        ids = []
        prices = []
        titles = []
        api_logs = []
        for href in hrefs:
            # Extract the article id from the link URL.
            article_id = href['href'].split('/artikal/')[1].split('/')[0]
            ids.append(article_id)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        for article_id in ids:
            start_time = time.time()
            try:
                response = requests.get(
                    f'https://api.olx.ba/listings/{article_id}',
                    headers=headers,
                    timeout=10
                )
                call_log = {
                    'article_id': article_id,
                    'status_code': response.status_code,
                    'response_time': f"{(time.time() - start_time):.2f}s",
                    'url': f'https://api.olx.ba/listings/{article_id}'
                }
                if response.status_code == 200:
                    data = response.json()
                    prices.append(data.get('display_price', '0'))
                    titles.append(data.get('title', ''))
                    call_log['success'] = True
                else:
                    print(f"API Error: Status {response.status_code} for ID {article_id}")
                    call_log['success'] = False
                api_logs.append(call_log)
            except requests.exceptions.RequestException as e:
                print(f"Request failed for ID {article_id}: {str(e)}")
                prices.append("0")
                titles.append("NO TITLE error 404")
                call_log = {
                    'article_id': article_id,
                    'success': False,
                    'error': str(e)
                }
                api_logs.append(call_log)
        browser.close()
        return {
            'prices': prices,
            'titles': titles,
            'hrefs': [f"https://olx.ba{h['href']}" for h in hrefs],
            'no_results': len(prices) == 0,
            'api_logs': api_logs
        }


def clean_prices(df):
    """
    Cleans price strings by removing currency symbols and formatting characters,
    then converts the values to numeric.
    """
    df['price'] = df['price'].replace('Na upit', pd.NA)
    df['price'] = df['price'].astype(str).str.replace('KM', '').str.replace('.', '').str.replace(',', '.').str.strip()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['price'])
    return df


def quantile_bounds_cleaning(df):
    Q1 = df['price'].quantile(0.25)
    Q3 = df['price'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    filtered_df = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)]
    return filtered_df


def remove_z_score_outliers(df):
    if df['price'].std() == 0:
        return df
    z_scores = abs((df['price'] - df['price'].mean()) / df['price'].std())
    df = df[z_scores <= 1]
    return df


def get_max_page_number(url, token):
    """
    Tries to find the maximum page number from the pagination elements.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            pagination = soup.select('li[data-v-4d6eb679]')
            if pagination:
                last_page = [li.text.strip() for li in pagination if li.text.strip().isdigit()]
                if last_page:
                    return int(last_page[-1])
            return 1
        except Exception as e:
            print(f"Error getting max page number: {e}")
            return 1
        finally:
            browser.close()


def scrape_all_pages(base_url, token, max_pages=10):
    """
    Loops over pages (up to max_pages) for a given search URL,
    accumulates titles, prices, and hrefs.
    """
    all_titles = []
    all_prices = []
    all_hrefs = []
    page = 1
    while page <= max_pages:
        current_url = f"{base_url}&page={page}"
        print(f"Scraping page {page} for URL: {current_url}")
        results = extract_data(current_url, token)
        if results['no_results']:
            print("No more results found.")
            break
        all_titles.extend(results['titles'])
        all_prices.extend(results['prices'])
        all_hrefs.extend(results['hrefs'])
        page += 1
    return all_titles, all_prices, all_hrefs


# ------------------------------
# OLX Login Functions
# ------------------------------

def get_credentials():
    """
    Returns OLX login credentials.
    (These are hardcoded for this integration; adjust as needed.)
    """
    username = 'snezabnf'
    password = 'conjevina12'
    return username, password


def login_to_olx(username, password, device_name="integration"):
    """
    Logs in to OLX via the API and returns an access token.
    """
    try:
        url = "https://api.olx.ba/auth/login"
        data = {
            "username": username,
            "password": password,
            "device_name": device_name
        }
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        json_response = response.json()
        return json_response.get('token')
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("Access forbidden. Please check your credentials.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None


# ------------------------------
# Item Processing and Price Averaging
# ------------------------------

def process_item(item_name, token, max_pages):
    """
    For a given item name (search query):
      - Constructs a search URL using the hardcoded category settings.
      - Scrapes up to max_pages of results.
      - Cleans and filters the prices, then computes the average price.
      - Returns a dictionary with the item, average price, total listings, and category info.
    """
    # Hardcoded category values:
    category_name = "Literatura"
    subcategory_name = "Knjige"
    # Hardcoded category_id – adjust to the correct OLX id if needed.
    category_id = "16"
    query = item_name.replace(" ", "+")
    base_url = f"https://olx.ba/pretraga?attr=&attr_encoded=1&q={query}&category_id={category_id}"
    print(f"\nProcessing item: '{item_name}' with search URL: {base_url}")

    # Scrape listings for the item.
    titles, prices, hrefs = scrape_all_pages(base_url, token, max_pages=max_pages)

    if not prices:
        print(f"No prices found for item: {item_name}")
        return {
            'item': item_name,
            'average_price': None,
            'total_listings': 0,
            'category': category_name,
            'subcategory': subcategory_name
        }

    # Create a DataFrame from prices and clean them.
    df = pd.DataFrame({'price': prices})
    df = clean_prices(df)
    if df.empty:
        print(f"No valid prices after cleaning for item: {item_name}")
        return {
            'item': item_name,
            'average_price': None,
            'total_listings': 0,
            'category': category_name,
            'subcategory': subcategory_name
        }
    df = quantile_bounds_cleaning(df)
    df = remove_z_score_outliers(df)
    if df.empty:
        average_price = None
    else:
        average_price = df['price'].mean()

    total_listings = len(prices)
    print(f"Item: {item_name} - Average Price: {average_price} KM from {total_listings} listings")
    return {
        'item': item_name,
        'average_price': average_price,
        'total_listings': total_listings,
        'category': category_name,
        'subcategory': subcategory_name
    }


# ------------------------------
# Main Function
# ------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="OLX Price Scraper: Reads a file of item names, collects prices from OLX, "
                    "calculates average prices per item, and saves the results to a CSV file."
    )
    parser.add_argument("--input", required=True, help="Input file with list of items (one per line)")
    parser.add_argument("--output", required=True, help="Output CSV file to save the results")
    parser.add_argument("--max_pages", type=int, default=10, help="Maximum number of pages to scrape per item")
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output
    max_pages = args.max_pages

    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' does not exist.")
        return

    # Read items from the input file.
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # If the line contains a colon (e.g., "1: Item Name"), extract the part after the colon.
        if ":" in line:
            parts = line.split(":", 1)
            item_name = parts[1].strip()
        else:
            item_name = line
        items.append(item_name)

    # Login to OLX.
    username, password = get_credentials()
    token = login_to_olx(username, password)
    if not token:
        print("Login failed!")
        return
    print("Successfully logged in!")

    results = []
    # Process each item sequentially.
    for item in items:
        result = process_item(item, token, max_pages)
        results.append(result)
        # Sleep between items to avoid rate-limiting.
        time.sleep(2)

    # Save the accumulated results to a CSV file.
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nDone! Results saved to '{output_file}'")


if __name__ == "__main__":
    main()

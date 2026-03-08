"""
RIG-Builder — Web Scraper Module
Fetches real-time pricing from multiple retailers with automatic fallback.
"""

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import time
import re
import urllib.parse


# ── Realistic Browser Headers ───────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
]


def _get_headers():
    """Return randomized browser-like headers."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _clean_price(price_text):
    """Extract numeric price from text like '$1,299.99' or '1299.99'."""
    if not price_text:
        return None
    match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


# ── Retailer Scrapers ───────────────────────────────────────────────────

def _scrape_amazon(query):
    """Search Amazon for a product and return the first result."""
    try:
        url = f"https://www.amazon.com/s?k={urllib.parse.quote(query)}&i=computers"
        resp = requests.get(url, headers=_get_headers(), timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select('[data-component-type="s-search-result"]')

        for item in results[:3]:
            title_el = item.select_one("h2 a span")
            price_whole = item.select_one(".a-price .a-price-whole")
            price_frac = item.select_one(".a-price .a-price-fraction")
            link_el = item.select_one("h2 a")

            if title_el and price_whole:
                price_str = price_whole.get_text(strip=True)
                if price_frac:
                    price_str += "." + price_frac.get_text(strip=True)
                price = _clean_price(price_str)
                if price and price > 10:
                    link = "https://www.amazon.com" + link_el.get("href", "") if link_el else ""
                    return {
                        "retailer": "Amazon",
                        "title": title_el.get_text(strip=True)[:100],
                        "price": price,
                        "url": link,
                        "in_stock": True,
                    }
    except Exception:
        pass
    return None


def _scrape_newegg(query):
    """Search Newegg for a product and return the first result."""
    try:
        url = f"https://www.newegg.com/p/pl?d={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=_get_headers(), timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".item-cell, .item-container")

        for item in items[:3]:
            title_el = item.select_one(".item-title, a.item-title")
            price_el = item.select_one(".price-current")

            if title_el and price_el:
                price = _clean_price(price_el.get_text(strip=True))
                link = title_el.get("href", "")
                if price and price > 10:
                    return {
                        "retailer": "Newegg",
                        "title": title_el.get_text(strip=True)[:100],
                        "price": price,
                        "url": link if link.startswith("http") else f"https://www.newegg.com{link}",
                        "in_stock": True,
                    }
    except Exception:
        pass
    return None


def _scrape_bhphoto(query):
    """Search B&H Photo for a product (fallback retailer)."""
    try:
        url = f"https://www.bhphotovideo.com/c/search?q={urllib.parse.quote(query)}&filters=fct_category%3Acomputers"
        resp = requests.get(url, headers=_get_headers(), timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select('[data-selenium="miniProductPage"]')

        for item in items[:3]:
            title_el = item.select_one('[data-selenium="miniProductPageName"]')
            price_el = item.select_one('[data-selenium="uppedDecimalPriceFirst"]')

            if title_el and price_el:
                price = _clean_price(price_el.get_text(strip=True))
                link_el = item.select_one("a[href]")
                link = link_el.get("href", "") if link_el else ""
                if price and price > 10:
                    return {
                        "retailer": "B&H Photo",
                        "title": title_el.get_text(strip=True)[:100],
                        "price": price,
                        "url": f"https://www.bhphotovideo.com{link}" if not link.startswith("http") else link,
                        "in_stock": True,
                    }
    except Exception:
        pass
    return None


def _scrape_bestbuy(query):
    """Search Best Buy for a product (fallback retailer)."""
    try:
        url = f"https://www.bestbuy.com/site/searchpage.jsp?st={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=_get_headers(), timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".sku-item, .list-item")

        for item in items[:3]:
            title_el = item.select_one(".sku-title a, .sku-header a")
            price_el = item.select_one('[data-testid="customer-price"] span')

            if title_el and price_el:
                price = _clean_price(price_el.get_text(strip=True))
                link = title_el.get("href", "")
                if price and price > 10:
                    return {
                        "retailer": "Best Buy",
                        "title": title_el.get_text(strip=True)[:100],
                        "price": price,
                        "url": f"https://www.bestbuy.com{link}" if not link.startswith("http") else link,
                        "in_stock": True,
                    }
    except Exception:
        pass
    return None


# ── Primary + Fallback Retailers ────────────────────────────────────────

PRIMARY_SCRAPERS = [
    ("Amazon", _scrape_amazon),
    ("Newegg", _scrape_newegg),
]

FALLBACK_SCRAPERS = [
    ("B&H Photo", _scrape_bhphoto),
    ("Best Buy", _scrape_bestbuy),
]


def scrape_component_prices(component_name, brand=""):
    """
    Scrape prices for a single component from multiple retailers.
    Tries primary retailers first, then falls back to alternates.
    
    Returns a list of price results from different retailers.
    """
    query = f"{brand} {component_name}".strip()
    results = []
    failed_primary = 0

    # Try primary retailers first
    for name, scraper_fn in PRIMARY_SCRAPERS:
        time.sleep(random.uniform(0.3, 0.8))  # Polite delay
        result = scraper_fn(query)
        if result:
            results.append(result)
        else:
            failed_primary += 1

    # If primary retailers failed, try fallback retailers
    if failed_primary > 0:
        for name, scraper_fn in FALLBACK_SCRAPERS:
            time.sleep(random.uniform(0.3, 0.8))
            result = scraper_fn(query)
            if result:
                results.append(result)
            if len(results) >= 2:
                break  # We have enough results

    return results


def scrape_all_components(components):
    """
    Scrape prices for all components in parallel using ThreadPoolExecutor.
    
    Args:
        components: list of dicts with at least 'name' and optionally 'brand'
    
    Returns:
        dict mapping component name to list of retailer price results
    """
    price_data = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_component = {}
        for comp in components:
            name = comp.get("name", "")
            brand = comp.get("brand", "")
            future = executor.submit(scrape_component_prices, name, brand)
            future_to_component[future] = name

        for future in as_completed(future_to_component):
            comp_name = future_to_component[future]
            try:
                result = future.result(timeout=30)
                price_data[comp_name] = result
            except Exception:
                price_data[comp_name] = []

    return price_data

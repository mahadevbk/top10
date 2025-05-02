import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import pickle
import os

# Cache file to store scraped data
CACHE_FILE = "movie_series_cache.pkl"
CACHE_DURATION = timedelta(days=1)

# Headers for web scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Function to load cached data
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            cache = pickle.load(f)
            if datetime.now() - cache["timestamp"] < CACHE_DURATION:
                return cache["data"]
    return None

# Function to save data to cache
def save_cache(data):
    cache = {"timestamp": datetime.now(), "data": data}
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)

# Function to scrape Rotten Tomatoes for top 10 movies/series by category
def scrape_rotten_tomatoes(category):
    url_map = {
        "Thrillers": "https://www.rottentomatoes.com/browse/movies_at_home/genres:mystery_and_thriller",
        "Drama": "https://www.rottentomatoes.com/browse/movies_at_home/genres:drama",
        "Comedy": "https://www.rottentomatoes.com/browse/movies_at_home/genres:comedy",
        "Sci-Fi": "https://www.rottentomatoes.com/browse/movies_at_home/genres:science_fiction"
    }
    url = url_map.get(category)
    if not url:
        st.error(f"No URL mapped for category: {category}")
        return []

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Raises error for 404, 500, etc.
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("a", class_="js-tile-link")[:10]  # Adjust class if needed
        results = []
        for item in items:
            title = item.find("span", class_="p--small").text.strip() if item.find("span", class_="p--small") else "N/A"
            rating = item.find("score-pairs")["criticsscore"] if item.find("score-pairs") and item.find("score-pairs")["criticsscore"] else "N/A"
            results.append({"title": title, "rotten_tomatoes": f"{rating}%"})
        return results
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP Error scraping Rotten Tomatoes for {category}: {e}")
        return []
    except Exception as e:
        st.error(f"Error scraping Rotten Tomatoes for {category}: {e}")
        return []

# Function to scrape IMDb for top 10 movies/series by category
def scrape_imdb(category):
    url_map = {
        "Thrillers": "https://www.imdb.com/search/title/?genres=thriller&title_type=feature,tv_series&sort=user_rating,desc",
        "Drama": "https://www.imdb.com/search/title/?genres=drama&title_type=feature,tv_series&sort=user_rating,desc",
        "Comedy": "https://www.imdb.com/search/title/?genres=comedy&title_type=feature,tv_series&sort=user_rating,desc",
        "Sci-Fi": "https://www.imdb.com/search/title/?genres=sci-fi&title_type=feature,tv_series&sort=user_rating,desc"
    }
    url = url_map.get(category)
    if not url:
        return []

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("div", class_="sc-b189961a-0 iqHBGn")[:10]  # Adjust class if needed
        results = []
        for item in items:
            title_elem = item.find("h3", class_="ipc-title__text")
            title = title_elem.text.strip().split(".", 1)[-1].strip() if title_elem else "N/A"
            rating_elem = item.find("span", class_="ipc-rating-star--rating")
            rating = rating_elem.text.strip() if rating_elem else "N/A"
            results.append({"title": title, "imdb": rating})
        return results
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP Error scraping IMDb for {category}: {e}")
        return []
    except Exception as e:
        st.error(f"Error scraping IMDb for {category}: {e}")
        return []

# Function to merge data from both sources
def merge_data(rt_data, imdb_data):
    merged = []
    seen_titles = set()
    
    # Start with Rotten Tomatoes data
    for rt_item in rt_data:
        title = rt_item["title"]
        if title not in seen_titles:
            merged_item = {"title": title, "rotten_tomatoes": rt_item["rotten_tomatoes"], "imdb": "N/A"}
            # Look for matching IMDb entry
            for imdb_item in imdb_data:
                if title.lower() in imdb_item["title"].lower() or imdb_item["title"].lower() in title.lower():
                    merged_item["imdb"] = imdb_item["imdb"]
                    break
            merged.append(merged_item)
            seen_titles.add(title)
    
    # Add remaining IMDb items if not already included
    for imdb_item in imdb_data:
        title = imdb_item["title"]
        if title not in seen_titles:
            merged.append({"title": title, "rotten_tomatoes": "N/A", "imdb": imdb_item["imdb"]})
            seen_titles.add(title)
    
    return merged[:10]  # Limit to top 10

# Main function to fetch or update data
def fetch_top_10_lists():
    cached_data = load_cache()
    if cached_data:
        return cached_data

    categories = ["Thrillers", "Drama", "Comedy", "Sci-Fi"]
    top_10_lists = {}

    for category in categories:
        st.write(f"Fetching data for {category}...")
        rt_data = scrape_rotten_tomatoes(category)
        imdb_data = scrape_imdb(category)
        merged_data = merge_data(rt_data, imdb_data)
        top_10_lists[category] = merged_data

    save_cache(top_10_lists)
    return top_10_lists

# Streamlit app
st.title("Top 10 Movies and Series by Category")
st.write("Updated daily with ratings from IMDb and Rotten Tomatoes")

# Fetch data
top_10_lists = fetch_top_10_lists()

# Display data for each category
for category, items in top_10_lists.items():
    st.subheader(category)
    if items:
        df = pd.DataFrame(items)
        df.index = df.index + 1  # 1-based indexing
        st.table(df[["title", "imdb", "rotten_tomatoes"]])
    else:
        st.write("No data available for this category.")

st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

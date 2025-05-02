import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import pickle
import os
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache file to store scraped data
CACHE_FILE = "movie_series_cache.pkl"
CACHE_DURATION = timedelta(days=1)

# Headers for web scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
                if datetime.now() - cache["timestamp"] < CACHE_DURATION:
                    return cache["data"]
        except Exception as e:
            st.warning(f"Error loading cache: {e}")
    return None

def save_cache(data):
    cache = {"timestamp": datetime.now(), "data": data}
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
    except Exception as e:
        st.error(f"Error saving cache: {e}")

def scrape_rotten_tomatoes(category, title_type):
    base_url = "https://www.rottentomatoes.com"
    path_map = {
        "Thrillers": {
            "movies": "/browse/movies_in_theaters/genres:thriller~sort:popular",
            "series": "/browse/tv_series_browse/genres:thriller~sort:popular"
        },
        "Drama": {
            "movies": "/browse/movies_in_theaters/genres:drama~sort:popular",
            "series": "/browse/tv_series_browse/genres:drama~sort:popular"
        },
        "Comedy": {
            "movies": "/browse/movies_in_theaters/genres:comedy~sort:popular",
            "series": "/browse/tv_series_browse/genres:comedy~sort:popular"
        },
        "Sci-Fi": {
            "movies": "/browse/movies_in_theaters/genres:sci_fi~sort:popular",
            "series": "/browse/tv_series_browse/genres:sci_fi~sort:popular"
        }
    }
    
    path = path_map.get(category, {}).get(title_type)
    if not path:
        return []
    
    url = f"{base_url}{path}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        tiles = soup.find_all("div", class_="js-tile-link")
        
        for tile in tiles[:10]:  # Limit to 10 items
            title_elem = tile.find("span", class_="p--small")
            title = title_elem.text.strip() if title_elem else "N/A"
            
            rating_elem = tile.find("score-pairs")
            if rating_elem:
                rating = rating_elem.get("criticsscore", "N/A")
            else:
                rating_elem = tile.find("span", class_="percentage")
                rating = rating_elem.text.strip().replace("%", "") if rating_elem else "N/A"
            
            if title != "N/A":
                results.append({
                    "title": title,
                    "rotten_tomatoes": f"{rating}%" if rating != "N/A" else "N/A"
                })
        
        return results
    except Exception as e:
        st.error(f"Error scraping Rotten Tomatoes for {category} ({title_type}): {e}")
        return []

def scrape_imdb(category, title_type):
    url_map = {
        "Thrillers": {
            "movies": "https://www.imdb.com/search/title/?title_type=feature&genres=thriller&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?title_type=tv_series&genres=thriller&sort=user_rating,desc&count=10"
        },
        "Drama": {
            "movies": "https://www.imdb.com/search/title/?title_type=feature&genres=drama&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?title_type=tv_series&genres=drama&sort=user_rating,desc&count=10"
        },
        "Comedy": {
            "movies": "https://www.imdb.com/search/title/?title_type=feature&genres=comedy&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?title_type=tv_series&genres=comedy&sort=user_rating,desc&count=10"
        },
        "Sci-Fi": {
            "movies": "https://www.imdb.com/search/title/?title_type=feature&genres=sci-fi&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?title_type=tv_series&genres=sci-fi&sort=user_rating,desc&count=10"
        }
    }
    
    url = url_map.get(category, {}).get(title_type)
    if not url:
        return []

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        items = soup.select(".lister-item")
        
        for item in items[:10]:  # Ensure we only get 10 items
            title_elem = item.find("h3", class_="lister-item-header")
            if title_elem:
                title = title_elem.find("a").text.strip()
            else:
                title = "N/A"
            
            rating_elem = item.find("div", class_="ratings-imdb-rating")
            rating = rating_elem.find("strong").text.strip() if rating_elem else "N/A"
            
            if title != "N/A":
                results.append({
                    "title": title,
                    "imdb": rating
                })
        
        return results
    except Exception as e:
        st.error(f"Error scraping IMDb for {category} ({title_type}): {e}")
        return []

def merge_data(rt_data, imdb_data):
    merged = []
    seen_titles = set()
    
    # First add all IMDb items
    for item in imdb_data:
        title = item["title"]
        if title not in seen_titles:
            rt_match = next((rt for rt in rt_data if similar_titles(title, rt["title"])), None)
            merged.append({
                "title": title,
                "imdb": item["imdb"],
                "rotten_tomatoes": rt_match["rotten_tomatoes"] if rt_match else "N/A"
            })
            seen_titles.add(title)
    
    # Then add remaining RT items (up to 10 total)
    for item in rt_data:
        if len(merged) >= 10:
            break
        if item["title"] not in seen_titles:
            merged.append({
                "title": item["title"],
                "imdb": "N/A",
                "rotten_tomatoes": item["rotten_tomatoes"]
            })
            seen_titles.add(item["title"])
    
    return merged[:10]

def similar_titles(title1, title2):
    # Simple similarity check
    t1 = re.sub(r'[^a-z0-9]', '', title1.lower())
    t2 = re.sub(r'[^a-z0-9]', '', title2.lower())
    return t1 in t2 or t2 in t1

def fetch_top_10_lists():
    cached_data = load_cache()
    if cached_data:
        return cached_data

    categories = ["Thrillers", "Drama", "Comedy", "Sci-Fi"]
    top_10_lists = {}

    for category in categories:
        rt_movies = scrape_rotten_tomatoes(category, "movies")
        rt_series = scrape_rotten_tomatoes(category, "series")
        imdb_movies = scrape_imdb(category, "movies")
        imdb_series = scrape_imdb(category, "series")
        
        top_10_lists[category] = {
            "movies": merge_data(rt_movies, imdb_movies),
            "series": merge_data(rt_series, imdb_series)
        }

    save_cache(top_10_lists)
    return top_10_lists

# Streamlit app
st.title("Top 10 Movies and Series by Category")
st.write("Updated daily with ratings from IMDb and Rotten Tomatoes")

# Fetch data
try:
    top_10_lists = fetch_top_10_lists()
except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# Display data for each category
for category, data in top_10_lists.items():
    st.subheader(category)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top 10 Movies**")
        movies = data.get("movies", [])
        if movies:
            df = pd.DataFrame(movies)
            df.index = df.index + 1
            st.table(df[["title", "imdb", "rotten_tomatoes"]])
        else:
            st.warning("No movies data available")
    
    with col2:
        st.markdown("**Top 10 TV Series**")
        series = data.get("series", [])
        if series:
            df = pd.DataFrame(series)
            df.index = df.index + 1
            st.table(df[["title", "imdb", "rotten_tomatoes"]])
        else:
            st.warning("No series data available")

st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

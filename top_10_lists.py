import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import pickle
import os
import logging

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

# Function to load cached data
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

# Function to save data to cache
def save_cache(data):
    cache = {"timestamp": datetime.now(), "data": data}
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
    except Exception as e:
        st.error(f"Error saving cache: {e}")

# Function to scrape Rotten Tomatoes for top movies/series by category
def scrape_rotten_tomatoes(category, title_type):
    url_map = {
        "Thrillers": {
            "movies": "https://www.rottentomatoes.com/browse/movies_at_home/genres:mystery_and_thriller~sort:popular",
            "series": "https://www.rottentomatoes.com/browse/tv_series_browse/genres:mystery_and_thriller~sort:popular"
        },
        "Drama": {
            "movies": "https://www.rottentomatoes.com/browse/movies_at_home/genres:drama~sort:popular",
            "series": "https://www.rottentomatoes.com/browse/tv_series_browse/genres:drama~sort:popular"
        },
        "Comedy": {
            "movies": "https://www.rottentomatoes.com/browse/movies_at_home/genres:comedy~sort:popular",
            "series": "https://www.rottentomatoes.com/browse/tv_series_browse/genres:comedy~sort:popular"
        },
        "Sci-Fi": {
            "movies": "https://www.rottentomatoes.com/browse/movies_at_home/genres:science_fiction~sort:popular",
            "series": "https://www.rottentomatoes.com/browse/tv_series_browse/genres:science_fiction~sort:popular"
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
        tiles = soup.find_all("div", {"data-qa": "discovery-media-list-item"})[:20]
        
        for tile in tiles:
            title_elem = tile.find("span", {"data-qa": "discovery-media-list-item-title"})
            title = title_elem.text.strip() if title_elem else "N/A"
            
            rating_elem = tile.find("score-pairs-deprecated")
            rating = rating_elem["criticsscore"] if rating_elem and "criticsscore" in rating_elem.attrs else "N/A"
            
            if title != "N/A":
                results.append({"title": title, "rotten_tomatoes": f"{rating}%"})
        
        return results[:10]
    except Exception as e:
        st.error(f"Error scraping Rotten Tomatoes for {category} ({title_type}): {e}")
        return []

# Function to scrape IMDb for top 10 movies or series by category
def scrape_imdb(category, title_type):
    url_map = {
        "Thrillers": {
            "movies": "https://www.imdb.com/search/title/?genres=thriller&title_type=feature&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?genres=thriller&title_type=tv_series&sort=user_rating,desc&count=10"
        },
        "Drama": {
            "movies": "https://www.imdb.com/search/title/?genres=drama&title_type=feature&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?genres=drama&title_type=tv_series&sort=user_rating,desc&count=10"
        },
        "Comedy": {
            "movies": "https://www.imdb.com/search/title/?genres=comedy&title_type=feature&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?genres=comedy&title_type=tv_series&sort=user_rating,desc&count=10"
        },
        "Sci-Fi": {
            "movies": "https://www.imdb.com/search/title/?genres=sci-fi&title_type=feature&sort=user_rating,desc&count=10",
            "series": "https://www.imdb.com/search/title/?genres=sci-fi&title_type=tv_series&sort=user_rating,desc&count=10"
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
        items = soup.select(".lister-item-header a")[:10]
        ratings = soup.select(".ratings-imdb-rating strong")[:10]
        
        for title_elem, rating_elem in zip(items, ratings):
            title = title_elem.text.strip()
            rating = rating_elem.text.strip()
            results.append({"title": title, "imdb": rating})
        
        return results
    except Exception as e:
        st.error(f"Error scraping IMDb for {category} ({title_type}): {e}")
        return []

# Function to merge data from both sources
def merge_data(rt_data, imdb_data, max_items=10):
    merged = []
    seen_titles = set()

    # Prioritize IMDb data as it's more specific to movie/series type
    for item in imdb_data:
        if len(merged) >= max_items:
            break
        title = item["title"]
        if title not in seen_titles:
            rt_rating = next((rt["rotten_tomatoes"] for rt in rt_data 
                            if rt["title"].lower() in title.lower() or title.lower() in rt["title"].lower()), "N/A")
            merged.append({
                "title": title,
                "imdb": item["imdb"],
                "rotten_tomatoes": rt_rating
            })
            seen_titles.add(title)

    # Add remaining RT items if we haven't reached max_items
    for item in rt_data:
        if len(merged) >= max_items:
            break
        if item["title"] not in seen_titles:
            merged.append({
                "title": item["title"],
                "imdb": "N/A",
                "rotten_tomatoes": item["rotten_tomatoes"]
            })
            seen_titles.add(item["title"])

    return merged[:max_items]

# Main function to fetch or update data
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

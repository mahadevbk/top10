import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import json
import os
from collections import defaultdict

# Configuration
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
CATEGORIES = ["Action", "Comedy", "Drama", "Sci-Fi", "Thriller"]
CACHE_FILE = "movie_data_cache.json"
CACHE_DURATION_HOURS = 12

# Helper functions
def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
                if (time.time() - cache["timestamp"]) < (CACHE_DURATION_HOURS * 3600):
                    return cache["data"]
    except Exception as e:
        st.warning(f"Cache loading error: {e}")
    return None

def save_cache(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": data}, f)
    except Exception as e:
        st.error(f"Error saving cache: {e}")

def clean_title(title):
    """Normalize titles for better matching"""
    if not title:
        return ""
    return title.lower().replace(":", "").replace("-", " ").strip()

# Scraping functions
def get_imdb_top(category, media_type="movie"):
    """Get top 10 from IMDb by category and media type"""
    base_url = "https://www.imdb.com/search/title/"
    genre_map = {
        "Action": "action",
        "Comedy": "comedy",
        "Drama": "drama",
        "Sci-Fi": "sci-fi",
        "Thriller": "thriller"
    }
    
    params = {
        "title_type": "feature" if media_type == "movie" else "tv_series",
        "genres": genre_map.get(category, category.lower()),
        "sort": "user_rating,desc",
        "count": 10
    }
    
    try:
        response = requests.get(base_url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        items = soup.select(".lister-item")[:10]
        
        for item in items:
            try:
                title_elem = item.find("h3", class_="lister-item-header")
                title = title_elem.find("a").text.strip() if title_elem else "N/A"
                
                rating_elem = item.find("div", class_="ratings-imdb-rating")
                rating = rating_elem.find("strong").text.strip() if rating_elem else "N/A"
                
                if title != "N/A":
                    results.append({
                        "title": title,
                        "imdb": rating,
                        "source": "IMDb"
                    })
            except Exception as e:
                st.warning(f"Error processing IMDb item: {e}")
                continue
        
        return results
    except Exception as e:
        st.error(f"IMDb {category} {media_type} error: {str(e)}")
        return []

def get_rotten_tomatoes_top(category, media_type="movie"):
    """Get top from Rotten Tomatoes"""
    # Updated URL structure for Rotten Tomatoes
    if media_type == "movie":
        url = f"https://www.rottentomatoes.com/browse/movies_in_theaters/genres:{category.lower()}"
    else:
        # For TV shows, we'll use the general TV browse page and filter in code
        url = "https://www.rottentomatoes.com/browse/tv_series_browse"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        
        # Different selectors for movies vs TV
        if media_type == "movie":
            tiles = soup.select("div[data-qa='discovery-media-list-item']")[:20]
        else:
            tiles = soup.select("div[data-qa='discovery-media-list-item']")[:20]
        
        for tile in tiles[:10]:  # Limit to 10 items
            try:
                title_elem = tile.find("span", {"data-qa": "discovery-media-list-item-title"})
                title = title_elem.text.strip() if title_elem else "N/A"
                
                # Get genre information to filter TV shows
                genre_elems = tile.find_all("span", class_="genre")
                genres = [g.text.strip().lower() for g in genre_elems] if genre_elems else []
                
                # Skip if this is a TV show and doesn't match our category
                if media_type == "tv" and category.lower() not in " ".join(genres):
                    continue
                
                score = tile.find("score-pairs")
                rating = score["criticsscore"] if score and "criticsscore" in score.attrs else "N/A"
                
                if title != "N/A":
                    results.append({
                        "title": title,
                        "rotten_tomatoes": f"{rating}%" if rating != "N/A" else rating,
                        "source": "Rotten Tomatoes"
                    })
            except Exception as e:
                st.warning(f"Error processing Rotten Tomatoes item: {e}")
                continue
        
        return results
    except Exception as e:
        st.error(f"Rotten Tomatoes {category} {media_type} error: {str(e)}")
        return []

# Data processing
def merge_sources(movie_data, tv_data):
    """Combine data from multiple sources"""
    combined = defaultdict(dict)
    
    for category in CATEGORIES:
        # Process movies
        movie_entries = []
        seen_movie_titles = set()
        
        for source in movie_data.get(category, {}).values():
            for item in source:
                clean = clean_title(item.get("title", ""))
                if clean and clean not in seen_movie_titles:
                    movie_entries.append({
                        "title": item.get("title", "N/A"),
                        "imdb": item.get("imdb", "N/A"),
                        "rotten_tomatoes": item.get("rotten_tomatoes", "N/A")
                    })
                    seen_movie_titles.add(clean)
        
        combined[category]["movies"] = movie_entries[:10]
        
        # Process TV series
        series_entries = []
        seen_series_titles = set()
        
        for source in tv_data.get(category, {}).values():
            for item in source:
                clean = clean_title(item.get("title", ""))
                if clean and clean not in seen_series_titles:
                    series_entries.append({
                        "title": item.get("title", "N/A"),
                        "imdb": item.get("imdb", "N/A"),
                        "rotten_tomatoes": item.get("rotten_tomatoes", "N/A")
                    })
                    seen_series_titles.add(clean)
        
        combined[category]["series"] = series_entries[:10]
    
    return combined

def fetch_all_data():
    """Fetch data from all sources"""
    try:
        cached = load_cache()
        if cached:
            return cached
        
        movie_data = defaultdict(dict)
        tv_data = defaultdict(dict)
        
        for category in CATEGORIES:
            # Fetch movie data
            movie_data[category]["imdb"] = get_imdb_top(category, "movie")
            movie_data[category]["rt"] = get_rotten_tomatoes_top(category, "movie")
            
            # Fetch TV data - only from IMDb for now as Rotten Tomatoes is unreliable
            tv_data[category]["imdb"] = get_imdb_top(category, "tv")
            # tv_data[category]["rt"] = get_rotten_tomatoes_top(category, "tv")
        
        combined = merge_sources(movie_data, tv_data)
        save_cache(combined)
        return combined
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return defaultdict(dict)

# Streamlit UI
def main():
    st.title("Top 10 Movies & TV Series by Category")
    st.write("""
    This app shows the current top rated movies and TV series across different genres.
    Data is refreshed every 12 hours.
    """)
    
    if st.button("Refresh Data"):
        if os.path.exists(CACHE_FILE):
            try:
                os.remove(CACHE_FILE)
                st.success("Cache cleared successfully! Refreshing data...")
            except Exception as e:
                st.error(f"Error clearing cache: {e}")
        st.experimental_rerun()
    
    data = fetch_all_data()
    
    for category in CATEGORIES:
        st.subheader(category)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Top Movies**")
            movies = data.get(category, {}).get("movies", [])
            if movies:
                df = pd.DataFrame(movies)
                df.index = df.index + 1
                st.table(df[["title", "imdb", "rotten_tomatoes"]])
            else:
                st.warning("No movie data available")
        
        with col2:
            st.markdown("**Top TV Series**")
            series = data.get(category, {}).get("series", [])
            if series:
                df = pd.DataFrame(series)
                df.index = df.index + 1
                st.table(df[["title", "imdb", "rotten_tomatoes"]])
            else:
                st.warning("No TV series data available")
    
    st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

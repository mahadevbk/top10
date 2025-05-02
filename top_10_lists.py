import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import json
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
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            if (time.time() - cache["timestamp"]) < (CACHE_DURATION_HOURS * 3600):
                return cache["data"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump({"timestamp": time.time(), "data": data}, f)

def clean_title(title):
    """Normalize titles for better matching"""
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
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        items = soup.select(".lister-item")[:10]
        
        for item in items:
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
        
        return results
    except Exception as e:
        st.error(f"IMDb {category} {media_type} error: {str(e)}")
        return []

def get_rotten_tomatoes_top(category, media_type="movie"):
    """Get top from Rotten Tomatoes"""
    genre_map = {
        "Action": "action__adventure",
        "Comedy": "comedy",
        "Drama": "drama",
        "Sci-Fi": "science_fiction__fantasy",
        "Thriller": "mystery__thriller"
    }
    
    media_path = "movies" if media_type == "movie" else "tv"
    url = f"https://www.rottentomatoes.com/browse/{media_path}_at_home/sort:popular?genres={genre_map.get(category, category.lower())}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        tiles = soup.select("div[data-qa='discovery-media-list-item']")[:10]
        
        for tile in tiles:
            title_elem = tile.find("span", {"data-qa": "discovery-media-list-item-title"})
            title = title_elem.text.strip() if title_elem else "N/A"
            
            score = tile.find("score-pairs")
            rating = score["criticsscore"] if score and "criticsscore" in score.attrs else "N/A"
            
            if title != "N/A":
                results.append({
                    "title": title,
                    "rotten_tomatoes": f"{rating}%" if rating != "N/A" else rating,
                    "source": "Rotten Tomatoes"
                })
        
        return results
    except Exception as e:
        st.error(f"Rotten Tomatoes {category} {media_type} error: {str(e)}")
        return []

# Data processing
def merge_sources(movie_data, tv_data):
    """Combine data from multiple sources"""
    combined = defaultdict(dict)
    
    # Process movie data
    for category in CATEGORIES:
        # Movies
        all_movies = []
        seen_titles = set()
        
        for source in movie_data[category].values():
            for item in source:
                clean = clean_title(item["title"])
                if clean not in seen_titles:
                    merged_item = {
                        "title": item["title"],
                        "imdb": item.get("imdb", "N/A"),
                        "rotten_tomatoes": item.get("rotten_tomatoes", "N/A")
                    }
                    all_movies.append(merged_item)
                    seen_titles.add(clean)
        
        combined[category]["movies"] = all_movies[:10]
        
        # TV Series
        all_series = []
        seen_titles = set()
        
        for source in tv_data[category].values():
            for item in source:
                clean = clean_title(item["title"])
                if clean not in seen_titles:
                    merged_item = {
                        "title": item["title"],
                        "imdb": item.get("imdb", "N/A"),
                        "rotten_tomatoes": item.get("rotten_tomatoes", "N/A")
                    }
                    all_series.append(merged_item)
                    seen_titles.add(clean)
        
        combined[category]["series"] = all_series[:10]
    
    return combined

def fetch_all_data():
    """Fetch data from all sources"""
    cached = load_cache()
    if cached:
        return cached
    
    movie_data = defaultdict(dict)
    tv_data = defaultdict(dict)
    
    for category in CATEGORIES:
        # Fetch movie data
        movie_data[category]["imdb"] = get_imdb_top(category, "movie")
        movie_data[category]["rt"] = get_rotten_tomatoes_top(category, "movie")
        
        # Fetch TV data
        tv_data[category]["imdb"] = get_imdb_top(category, "tv")
        tv_data[category]["rt"] = get_rotten_tomatoes_top(category, "tv")
    
    combined = merge_sources(movie_data, tv_data)
    save_cache(combined)
    return combined

# Streamlit UI
def main():
    st.title("Top 10 Movies & TV Series by Category")
    st.write("""
    This app shows the current top rated movies and TV series across different genres.
    Data is refreshed every 12 hours.
    """)
    
    if st.button("Refresh Data"):
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
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

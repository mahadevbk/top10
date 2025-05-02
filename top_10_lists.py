import streamlit as st
import requests
from datetime import datetime
import pytz
from imdb import Cinemagoer
from bs4 import BeautifulSoup

# ----------------------------- Configuration -----------------------------
API_KEY = "a7cb59b552915493b4103cd95c5285dd"  # Replace with your TMDB API key
BASE_TMDB_URL = "https://api.themoviedb.org/3"
TIMEZONE = pytz.timezone("Asia/Dubai")  # UTC+4

# ----------------------------- Utility Functions -----------------------------
def get_current_time():
    now = datetime.now(TIMEZONE)
    return now.strftime("%B %d, %Y at %I:%M %p")

@st.cache_data
def fetch_tmdb_genres(media_type='movie'):
    url = f"{BASE_TMDB_URL}/genre/{media_type}/list"
    response = requests.get(url, params={"api_key": API_KEY, "language": "en-US"})
    if response.status_code == 200:
        return {genre["name"]: genre["id"] for genre in response.json().get("genres", [])}
    else:
        return {}

def fetch_tmdb_titles(genre_id, media_type='movie'):
    url = f"{BASE_TMDB_URL}/discover/{media_type}"
    params = {
        "api_key": API_KEY,
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "language": "en-US",
        "page": 1,
        "primary_release_date.gte": "2020-01-01" if media_type == "movie" else None,
        "first_air_date.gte": "2020-01-01" if media_type == "tv" else None
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])[:10]
    else:
        return []

def fetch_imdb_titles(genre_name, media_type='movie'):
    ia = Cinemagoer()
    try:
        if media_type == 'movie':
            movies = ia.get_top50_movies_by_genres(genre_name.lower())
        else:
            movies = ia.get_top50_tv_by_genres(genre_name.lower())
        titles = []
        for movie in movies[:10]:
            ia.update(movie)
            titles.append({
                "title": movie.get('title'),
                "year": movie.get('year'),
                "rating": movie.get('rating'),
                "poster_url": movie.get('full-size cover url'),
                "link": f"https://www.imdb.com/title/tt{movie.movieID}/"
            })
        return titles
    except Exception as e:
        st.error(f"Error fetching data from IMDb: {e}")
        return []

def fetch_rt_titles(genre_name, media_type='movie'):
    # Note: Rotten Tomatoes does not provide a public API.
    # This function uses web scraping, which may break if the website structure changes.
    # Use with caution and respect the website's terms of service.
    try:
        genre_formatted = genre_name.lower().replace(' ', '_')
        url = f"https://www.rottentomatoes.com/top/bestofrt/top_100_{genre_formatted}_movies/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            st.warning("Could not retrieve data from Rotten Tomatoes.")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'table'})
        if not table:
            st.warning("No data table found on Rotten Tomatoes page.")
            return []

        rows = table.find_all('tr')[1:11]  # Skip header row and get top 10
        titles = []
        for row in rows:
            columns = row.find_all('td')
            if len(columns) < 3:
                continue
            rank = columns[0].text.strip()
            title_column = columns[2]
            title_link = title_column.find('a')
            title = title_link.text.strip() if title_link else "N/A"
            link = f"https://www.rottentomatoes.com{title_link['href']}" if title_link else None
            rating = columns[1].text.strip()
            titles.append({
                "title": title,
                "year": "N/A",
                "rating": rating,
                "poster_url": None,
                "link": link
            })
        return titles
    except Exception as e:
        st.error(f"Error fetching data from Rotten Tomatoes: {e}")
        return []

# ----------------------------- Streamlit App -----------------------------
st.set_page_config(layout="centered")
st.image("top10image.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🎬 Top 10 Movies & TV Series</h1>", unsafe_allow_html=True)

# Source, Media Type, and Genre Selection
source = st.radio("Select Source", ["TMDB", "IMDb", "Rotten Tomatoes"], horizontal=True)
media_type = st.radio("Media Type", ["movie", "tv"], horizontal=True)

if source == "TMDB":
    genres = fetch_tmdb_genres(media_type)
    if genres:
        genre_name = st.selectbox("Select Genre", list(genres.keys()))
        genre_id = genres[genre_name]
    else:
        st.error("Failed to fetch genres from TMDB.")
        genre_name = ""
        genre_id = None
else:
    genre_name = st.text_input("Enter Genre (e.g., Action, Comedy)", value="Action")
    genre_id = None

# Timestamp
timestamp = get_current_time()
st.markdown(f"<p style='text-align: center;'><em>Updated on: {timestamp} (UTC+4)</em></p>", unsafe_allow_html=True)

# Fetch and Display Titles
if source == "TMDB" and genre_id:
    titles = fetch_tmdb_titles(genre_id, media_type)
elif source == "IMDb":
    titles = fetch_imdb_titles(genre_name, media_type)
elif source == "Rotten Tomatoes":
    titles = fetch_rt_titles(genre_name, media_type)
else:
    titles = []

if not titles:
    st.markdown("<p style='text-align: center;'>No titles found.</p>", unsafe_allow_html=True)
else:
    for idx, title in enumerate(titles, start=1):
        name = title.get("title", "N/A")
        year = title.get("year", "N/A")
        rating = title.get("rating", "N/A")
        poster_url = title.get("poster_url")
        link = title.get("link")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if poster_url:
                st.image(poster_url, use_column_width=True)
            st.markdown(f"<h4 style='text-align: center;'>{idx}. {name} ({year})</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>⭐ Rating: {rating}</p>", unsafe_allow_html=True)
            if link:
                st.markdown(f"<p style='text-align: center;'><a href='{link}' target='_blank'>🔗 View Details</a></p>", unsafe_allow_html=True)
            st.markdown("<hr>", unsafe_allow_html=True)

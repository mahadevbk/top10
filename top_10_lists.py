import streamlit as st
import requests
from imdb import Cinemagoer
from datetime import datetime
import pytz

# ---- CONFIGURATION ----
TMDB_API_KEY = "a7cb59b552915493b4103cd95c5285dd"
OMDB_API_KEY = "e3f26c76"
TIMEZONE = pytz.timezone("Asia/Dubai")  # UTC+4
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# ---- HELPER FUNCTIONS ----

def get_current_time():
    now = datetime.now(TIMEZONE)
    return now.strftime("%B %d, %Y at %I:%M %p")

@st.cache_data
def fetch_tmdb_genres(media_type="movie"):
    url = f"{TMDB_BASE_URL}/genre/{media_type}/list"
    res = requests.get(url, params={"api_key": TMDB_API_KEY, "language": "en-US"})
    return {g["name"]: g["id"] for g in res.json().get("genres", [])}

def fetch_tmdb_titles(genre_id, media_type="movie"):
    url = f"{TMDB_BASE_URL}/discover/{media_type}"
    params = {
        "api_key": TMDB_API_KEY,
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "language": "en-US",
        "page": 1,
        "include_adult": False,
    }
    if media_type == "movie":
        params["primary_release_date.gte"] = "2020-01-01"
    else:
        params["first_air_date.gte"] = "2020-01-01"
    res = requests.get(url, params=params)
    results = res.json().get("results", [])[:10]
    titles = []
    for r in results:
        lang = r.get("original_language", "en")
        if lang != "en":
            continue
        titles.append({
            "title": r.get("title") or r.get("name"),
            "year": (r.get("release_date") or r.get("first_air_date") or "N/A")[:4],
            "rating": r.get("vote_average", "N/A"),
            "poster_url": f"https://image.tmdb.org/t/p/w500{r.get('poster_path')}" if r.get("poster_path") else None,
            "link": f"https://www.themoviedb.org/{media_type}/{r.get('id')}"
        })
    return titles

def fetch_imdb_titles(genre_name, media_type="movie"):
    ia = Cinemagoer()
    try:
        search_results = ia.search_movie(genre_name)
        titles = []
        for m in search_results:
            ia.update(m)
            if 'genres' in m and genre_name.capitalize() in m['genres'] and m.get('language') != 'Non-English':
                titles.append({
                    "title": m.get("title"),
                    "year": m.get("year"),
                    "rating": m.get("rating"),
                    "poster_url": m.get("full-size cover url"),
                    "link": f"https://www.imdb.com/title/tt{m.movieID}/"
                })
            if len(titles) >= 10:
                break
        return titles
    except Exception as e:
        st.error(f"IMDb fetch error: {e}")
        return []

def fetch_rt_titles(genre_name):
    popular_titles = ["The Batman", "Oppenheimer", "Knives Out", "Parasite", "Top Gun: Maverick",
                      "Dune", "Nope", "Glass Onion", "The Menu", "Tenet"]
    titles = []
    for t in popular_titles:
        res = requests.get(f"http://www.omdbapi.com/?t={t}&apikey={OMDB_API_KEY}")
        data = res.json()
        if data.get("Response") == "True" and genre_name.lower() in data.get("Genre", "").lower():
            rt_rating = next((r['Value'] for r in data.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), "N/A")
            if data.get("Language", "").startswith("English"):
                titles.append({
                    "title": data.get("Title"),
                    "year": data.get("Year"),
                    "rating": rt_rating,
                    "poster_url": data.get("Poster"),
                    "link": f"https://www.rottentomatoes.com/m/{data.get('Title').lower().replace(' ', '_')}"
                })
        if len(titles) >= 10:
            break
    return titles

# ---- STREAMLIT LAYOUT ----

st.set_page_config(layout="centered")
st.image("top10image.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🎬 Top 10 Movies & TV Shows</h1>", unsafe_allow_html=True)

source = st.radio("Select Source", ["TMDB", "IMDb", "Rotten Tomatoes"], horizontal=True)
media_type = st.radio("Media Type", ["movie", "tv"], horizontal=True if source == "TMDB" else False)

if source == "TMDB":
    genres = fetch_tmdb_genres(media_type)
    genre_name = st.selectbox("Select Genre", list(genres.keys()))
    genre_id = genres[genre_name]
else:
    genre_name = st.text_input("Enter Genre", "Action")

# Show update time
st.markdown(f"<p style='text-align: center;'>📅 Updated on: <strong>{get_current_time()}</strong> (UTC+4)</p>",
            unsafe_allow_html=True)

# Fetch and display titles
if source == "TMDB":
    titles = fetch_tmdb_titles(genre_id, media_type)
elif source == "IMDb":
    titles = fetch_imdb_titles(genre_name, media_type)
else:
    titles = fetch_rt_titles(genre_name)

if not titles:
    st.warning("No results found for the selected source/genre.")
else:
    for idx, t in enumerate(titles, start=1):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if t.get("poster_url"):
                st.image(t["poster_url"], use_container_width=True)
            st.markdown(f"### {idx}. {t['title']} ({t['year']})", unsafe_allow_html=True)
            st.markdown(f"⭐ **Rating**: {t['rating']}")
            if t.get("link"):
                st.markdown(f"[🔗 More Info]({t['link']})")
            st.markdown("---")

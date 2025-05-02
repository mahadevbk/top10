import streamlit as st
import requests

API_KEY = "a7cb59b552915493b4103cd95c5285dd"  # Replace with your TMDB API key
BASE_URL = "https://api.themoviedb.org/3"

st.set_page_config(layout="centered")

# --- Display Top Image ---
#st.image("top10image.png", use_container_width=True)  # <-- Add your top image file path here

@st.cache_data
def fetch_genres(media_type='movie'):
    url = f"{BASE_URL}/genre/{media_type}/list"
    response = requests.get(url, params={"api_key": API_KEY, "language": "en-US"})
    return {genre["name"]: genre["id"] for genre in response.json().get("genres", [])}

def fetch_titles(genre_id, media_type='movie'):
    url = f"{BASE_URL}/discover/{media_type}"
    params = {
        "api_key": API_KEY,
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "language": "en-US",  # Filters content to English only
        "page": 1,
        "primary_release_date.gte": "2020-01-01" if media_type == "movie" else None,
        "first_air_date.gte": "2020-01-01" if media_type == "tv" else None
    }
    response = requests.get(url, params=params)
    return response.json().get("results", [])[:10]

# --- Page Header ---
st.markdown("<h1 style='text-align: center;'>🎥 TMD Top rated Movies & TV Series by Genre</h1>", unsafe_allow_html=True)

# --- Widget Columns ---
left, center, right = st.columns([1, 2, 1])
with center:
    media_type = st.radio("Select Media Type", ["movie", "tv"], horizontal=True)
    genres = fetch_genres(media_type)
    genre_name = st.selectbox("Select Genre", list(genres.keys()))
    genre_id = genres[genre_name]

# --- Section Title ---
st.markdown(f"<h2 style='text-align: center;'>Top 10 {genre_name} {'Movies' if media_type == 'movie' else 'TV Series'}</h2>", unsafe_allow_html=True)

# --- Display Results ---
titles = fetch_titles(genre_id, media_type)

if not titles:
    st.markdown("<p style='text-align: center;'>No recent titles found.</p>", unsafe_allow_html=True)
else:
    for title in titles:
        name = title.get("title") or title.get("name")
        year = (title.get("release_date") or title.get("first_air_date") or "")[:4]
        rating = title.get("vote_average", "N/A")
        tmdb_id = title["id"]
        poster_path = title.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        link = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"

        # Center everything inside a single wide column
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if poster_url:
                st.image(poster_url, use_container_width=True)
            st.markdown(f"<h4 style='text-align: center;'>{name} ({year})</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>⭐ Rating: {rating}/10</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'><a href='{link}' target='_blank'>🔗 View on TMDB</a></p>", unsafe_allow_html=True)
            st.markdown("<hr>", unsafe_allow_html=True)

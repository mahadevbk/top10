import streamlit as st
import requests

st.set_page_config(layout="centered")

# Custom CSS to center text
st.markdown("""
    <style>
    .centered {
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Display the poster image at the top
st.image("top10image.png", use_container_width=223)

API_KEY = "a7cb59b552915493b4103cd95c5285dd"  # <-- Insert your TMDB API key here
BASE_URL = "https://api.themoviedb.org/3"

# Fetch available genres from TMDB
@st.cache_data
def fetch_genres(media_type='movie'):
    url = f"{BASE_URL}/genre/{media_type}/list"
    response = requests.get(url, params={"api_key": API_KEY, "language": "en-US"})
    data = response.json()
    return {genre["name"]: genre["id"] for genre in data.get("genres", [])}

# Fetch top titles based on genre and type
def fetch_titles(genre_id, media_type='movie'):
    url = f"{BASE_URL}/discover/{media_type}"
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
    return response.json().get("results", [])[:10]

st.title("🎥 Recent Movies & TV Series by Genre (IMDb-style via TMDB)")

# Let user choose between movies and TV
media_type = st.radio("Select Media Type", ["movie", "tv"])

# Dynamically load genres for the selected media type
genres = fetch_genres(media_type)
genre_name = st.selectbox("Select a Genre", list(genres.keys()))
genre_id = genres[genre_name]

# Display recent titles
title_type = "Movies" if media_type == "movie" else "TV Series"
st.subheader(f"🔥 Top 10 Recent {genre_name} {title_type}")

titles = fetch_titles(genre_id, media_type)
if not titles:
    st.write("No recent titles found.")
else:
    for title in titles:
        name = title.get("title") or title.get("name")
        year = title.get("release_date", "")[:4] or title.get("first_air_date", "")[:4]
        rating = title.get("vote_average", "N/A")
        tmdb_id = title.get("id")
        link = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"

        st.markdown(f"**{name} ({year})**")
        st.markdown(f"⭐ Rating: {rating}/10")
        st.markdown(f"[🔗 View on TMDB]({link})")
        st.markdown("---")

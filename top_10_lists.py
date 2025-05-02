import streamlit as st
import requests

API_KEY = "a7cb59b552915493b4103cd95c5285dd"  # <-- Replace this with your key
BASE_URL = "https://api.themoviedb.org/3"

GENRES = {
    "Thriller": 53,
    "Medical Dramas": 18,  # No strict category for "Medical", so we use Drama
    "Comedy": 35,
    "Murder Mystery": 9648,  # Mystery
    "Sci-Fi": 878
}

def fetch_tmdb_list(genre_id, media_type='movie'):
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
    data = response.json()
    return data.get("results", [])[:10]  # Top 10

st.title("🎬 Recent Top Movies & TV Series by Genre (via TMDB API)")

genre_name = st.selectbox("Select a Genre", list(GENRES.keys()))
genre_id = GENRES[genre_name]

st.subheader(f"🎬 Top 10 Recent {genre_name} Movies")
movies = fetch_tmdb_list(genre_id, "movie")
if not movies:
    st.write("No recent movies found.")
for movie in movies:
    st.markdown(f"**{movie['title']} ({movie.get('release_date', 'N/A')[:4]})**")
    st.markdown(f"Rating: {movie.get('vote_average', 'N/A')}/10")
    st.markdown(f"[View on TMDB](https://www.themoviedb.org/movie/{movie['id']})")
    st.markdown("---")

st.subheader(f"📺 Top 10 Recent {genre_name} TV Series")
series = fetch_tmdb_list(genre_id, "tv")
if not series:
    st.write("No recent TV shows found.")
for show in series:
    st.markdown(f"**{show['name']} ({show.get('first_air_date', 'N/A')[:4]})**")
    st.markdown(f"Rating: {show.get('vote_average', 'N/A')}/10")
    st.markdown(f"[View on TMDB](https://www.themoviedb.org/tv/{show['id']})")
    st.markdown("---")

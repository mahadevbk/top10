import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Function to fetch recent titles from IMDb
def fetch_imdb_titles(genre, content_type='movie', count=10):
    """
    Fetches recent titles from IMDb based on genre and content type.
    """
    base_url = "https://www.imdb.com/search/title/"
    params = {
        'genres': genre.lower(),
        'title_type': content_type,
        'sort': 'year,desc',
        'count': count
    }
    response = requests.get(base_url, params=params)
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = []
    for item in soup.select('.lister-item'):
        header = item.select_one('.lister-item-header a')
        year = item.select_one('.lister-item-year')
        rating = item.select_one('.ratings-imdb-rating strong')
        if header:
            title = header.text
            link = "https://www.imdb.com" + header['href']
            year_text = year.text if year else 'N/A'
            rating_text = rating.text if rating else 'N/A'
            titles.append({
                'Title': title,
                'Year': year_text,
                'IMDb Rating': rating_text,
                'Link': link
            })
    return titles

# Function to fetch Rotten Tomatoes rating
def fetch_rt_rating(title):
    """
    Placeholder function for fetching Rotten Tomatoes rating.
    In practice, this would involve searching Rotten Tomatoes and parsing the rating.
    """
    # Due to the complexity of scraping Rotten Tomatoes, this function returns 'N/A'.
    return 'N/A'

# Streamlit App
st.title("🎥 Recent Movies and TV Series by Genre")
genres = ['Thriller', 'Medical Dramas', 'Comedy', 'Murder Mystery', 'Sci-Fi']
selected_genre = st.selectbox("Select a Genre", genres)

# Map genre to IMDb genre keywords
genre_mapping = {
    'Thriller': 'thriller',
    'Medical Dramas': 'drama',
    'Comedy': 'comedy',
    'Murder Mystery': 'mystery',
    'Sci-Fi': 'sci-fi'
}

# Display recent movies
st.subheader(f"🎬 Recent {selected_genre} Movies")
with st.spinner('Fetching data...'):
    movies = fetch_imdb_titles(genre_mapping[selected_genre], 'movie')
    for movie in movies:
        rt_rating = fetch_rt_rating(movie['Title'])
        st.markdown(f"**{movie['Title']} ({movie['Year']})**")
        st.markdown(f"IMDb Rating: {movie['IMDb Rating']}")
        st.markdown(f"Rotten Tomatoes Rating: {rt_rating}")
        st.markdown(f"[More Info]({movie['Link']})")
        st.markdown("---")

# Display recent TV series
st.subheader(f"📺 Recent {selected_genre} TV Series")
with st.spinner('Fetching data...'):
    series = fetch_imdb_titles(genre_mapping[selected_genre], 'tv_series')
    for show in series:
        rt_rating = fetch_rt_rating(show['Title'])
        st.markdown(f"**{show['Title']} ({show['Year']})**")
        st.markdown(f"IMDb Rating: {show['IMDb Rating']}")
        st.markdown(f"Rotten Tomatoes Rating: {rt_rating}")
        st.markdown(f"[More Info]({show['Link']})")
        st.markdown("---")

import streamlit as st
from imdb import IMDb

# Initialize IMDb access
ia = IMDb()

# Map genres to search-friendly IMDb categories
genre_map = {
    "Thriller": "thriller",
    "Medical Dramas": "drama",
    "Comedy": "comedy",
    "Murder Mystery": "mystery",
    "Sci-Fi": "sci-fi"
}

st.title("🎬 Recent Movies and TV Series by Genre")

selected_genre = st.selectbox("Select a Genre", list(genre_map.keys()))

def get_titles_by_genre(genre, content_type='movie'):
    search_results = ia.get_top250_movies() if content_type == 'movie' else ia.get_top250_tv()
    titles = []

    for item in search_results:
        try:
            ia.update(item)
            if 'genres' in item and genre.lower() in [g.lower() for g in item['genres']]:
                year = item.get('year', 'N/A')
                if year and int(year) >= 2015:  # Filter recent
                    titles.append({
                        "Title": item['title'],
                        "Year": year,
                        "IMDb Rating": item.get('rating', 'N/A'),
                        "Link": f"https://www.imdb.com/title/tt{item.movieID}/"
                    })
            if len(titles) >= 10:
                break
        except Exception:
            continue

    return titles

# Display recent Movies
st.subheader(f"🎬 Top Recent {selected_genre} Movies")
movies = get_titles_by_genre(genre_map[selected_genre], content_type='movie')
if not movies:
    st.write("No recent movies found.")
for movie in movies:
    st.markdown(f"**{movie['Title']} ({movie['Year']})**")
    st.markdown(f"IMDb Rating: {movie['IMDb Rating']']}")
    st.markdown(f"[More Info]({movie['Link']})")
    st.markdown("---")

# Display recent TV Shows
st.subheader(f"📺 Top Recent {selected_genre} TV Series")
series = get_titles_by_genre(genre_map[selected_genre], content_type='tv')
if not series:
    st.write("No recent TV shows found.")
for show in series:
    st.markdown(f"**{show['Title']} ({show['Year']})**")
    st.markdown(f"IMDb Rating: {show['IMDb Rating']}")
    st.markdown(f"[More Info]({show['Link']})")
    st.markdown("---")

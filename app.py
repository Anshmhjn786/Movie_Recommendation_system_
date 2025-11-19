import streamlit as st
import pickle
import pandas as pd
import requests

TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"  # consider moving to env var

def fetch_poster(movie_id):
    """Return poster URL for a numeric TMDB movie id, or None on failure."""
    if movie_id is None:
        return None
    try:
        movie_id = int(movie_id)
    except Exception:
        return None

    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        resp = requests.get(url, params={"api_key": TMDB_API_KEY, "language": "en-US"}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        poster_path = data.get("poster_path")
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        return None
    return None


def _get_movie_id_from_row(row):
    """Try common column names for ID inside the movies dataframe row."""
    for col in ("movie_id", "id", "tmdb_id"):
        if col in row.index and pd.notna(row[col]):
            return row[col]
    return None


def recommend(movie_title):
    """Return (titles, poster_urls) lists of 5 recommendations."""
    try:
        movie_index = movies[movies['title'] == movie_title].index[0]
    except Exception:
        return [], []

    distances = similarity[movie_index]
    # top 5 excluding the selected movie itself
    movies_list = sorted(list(enumerate(distances)), key=lambda x: x[1], reverse=True)[1:6]

    recommended_movies = []
    recommended_movies_posters = []

    for idx, _score in movies_list:
        row = movies.iloc[idx]
        title = row.get('title', 'Unknown')
        recommended_movies.append(title)

        movie_id = _get_movie_id_from_row(row)
        # fallback: search TMDB by title if we lack an id
        if movie_id is None:
            try:
                q = requests.get(
                    "https://api.themoviedb.org/3/search/movie",
                    params={"api_key": TMDB_API_KEY, "query": title, "language": "en-US"},
                    timeout=5
                )
                q.raise_for_status()
                results = q.json().get("results", [])
                if results:
                    movie_id = results[0].get("id")
            except Exception:
                movie_id = None

        poster = fetch_poster(movie_id) if movie_id is not None else None
        if poster is None:
            # simple placeholder image URL
            poster = "https://via.placeholder.com/300x450?text=No+Poster"
        recommended_movies_posters.append(poster)

    return recommended_movies, recommended_movies_posters


# --- load pickles ---
movies_dict = pickle.load(open('movies_dict.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open('similarity.pkl', 'rb'))

# --- UI ---
st.title('Movie Recommender System')

selected_movie_name = st.selectbox(
    'Select a movie to get recommendations:',
    movies['title'].values
)

if st.button('Recommend'):
    names, posters = recommend(selected_movie_name)

    if not names:
        st.write("No recommendations found.")
    else:
        cols = st.columns(5)
        for i, col in enumerate(cols):
            with col:
                st.text(names[i])
                # use_container_width (not use_column_width)
                st.image(posters[i], use_container_width=True)

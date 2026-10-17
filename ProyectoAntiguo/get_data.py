"""
Descarga y limpia el dataset de canciones de Spotify (popularidad + audio features).

Fuente: "Spotify Tracks Dataset" (maharshipandya, Hugging Face / Kaggle),
~114k canciones obtenidas de la API de Spotify. Se usa este dataset porque
desde noviembre de 2024 la API de Spotify bloquea el endpoint de
audio-features para aplicaciones nuevas.

Uso:  python get_data.py
Salida: data/spotify_tracks_raw.csv  y  data/spotify_tracks_clean.csv
"""
from pathlib import Path

import pandas as pd

URL = "https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset/resolve/main/dataset.csv"
DATA_DIR = Path(__file__).parent / "data"
RAW_PATH = DATA_DIR / "spotify_tracks_raw.csv"
CLEAN_PATH = DATA_DIR / "spotify_tracks_clean.csv"

COLUMNS = [
    "track_id", "track_name", "artists", "album_name", "track_genre",
    "popularity",  # variable respuesta (0-100)
    "danceability", "energy", "valence", "acousticness", "instrumentalness",
    "speechiness", "liveness", "loudness", "tempo", "duration_ms",
    "key", "mode", "time_signature", "explicit",
]


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if RAW_PATH.exists():
        df = pd.read_csv(RAW_PATH, index_col=0)
    else:
        df = pd.read_csv(URL, index_col=0)
        df.to_csv(RAW_PATH)

    df = (
        df[COLUMNS]
        .dropna()
        .drop_duplicates(subset="track_id")  # una canción aparece en varios géneros
        .reset_index(drop=True)
    )
    df["explicit"] = df["explicit"].astype(int)

    df.to_csv(CLEAN_PATH, index=False)
    print(f"Guardado {CLEAN_PATH} -> {df.shape[0]} canciones, {df.shape[1]} columnas")


if __name__ == "__main__":
    main()

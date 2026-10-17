"""
Dataset de canciones ACTUALES: Top 200 diario de Spotify de varios países + audio features.

Fuentes:
  - Charts: kworb.net (réplica diaria de los Spotify Daily Top 200 por país),
    con streams diarios, streams de 7 días, días en el chart, pico y total.
  - Audio features: API pública de ReccoBeats (sin clave). Sustituye al endpoint
    /audio-features de Spotify, bloqueado para apps nuevas desde nov. 2024.

Nota: la API de Spotify ya no permite obtener 'popularity' ni 'audio-features'
con una app nueva, así que como medida de popularidad se usan los streams
diarios del chart (se recomienda usar log(streams) como variable respuesta).

Uso:  python get_current_data.py
Salida (en data/):
  - spotify_top200_countries_<fecha>.csv : una fila por (país, canción)
  - spotify_top200_songs_<fecha>.csv     : una fila por canción única
"""
import html
import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

CHART_URL = "https://kworb.net/spotify/country/{code}_daily.html"
FEATURES_URL = "https://api.reccobeats.com/v1/audio-features"
DATA_DIR = Path(__file__).parent / "data"

# Códigos de país de kworb (Reino Unido es "gb"). Añade o quita los que quieras.
COUNTRIES = {
    "es": "España",
    "us": "Estados Unidos",
    "fr": "Francia",
    "gb": "Reino Unido",
    "de": "Alemania",
    "it": "Italia",
    "mx": "México",
    "br": "Brasil",
    "ar": "Argentina",
    "ca": "Canadá",
    "au": "Australia",
    "nl": "Países Bajos",
}

FEATURES = [
    "danceability", "energy", "valence", "acousticness", "instrumentalness",
    "speechiness", "liveness", "loudness", "tempo", "key", "mode",
]


def _to_int(s: str) -> int:
    return int(s.replace(",", "").replace("+", "")) if s.strip() not in ("", "=") else 0


def get_chart(code: str) -> pd.DataFrame:
    """Descarga y parsea el Top 200 diario de un país desde kworb."""
    page = requests.get(CHART_URL.format(code=code), timeout=30)
    page.raise_for_status()
    page.encoding = "utf-8"
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page.text.split("<tbody>")[1], flags=re.S)

    records = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
        title_cell = cells[2]
        match = re.search(r"track/([A-Za-z0-9]{22})", title_cell)
        if match is None:
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", title_cell))
        artist, title = text.split(" - ", 1)
        records.append({
            "rank": _to_int(cells[0]),
            "track_id": match.group(1),
            "artist": artist.strip(),
            "title": title.strip(),
            "days_on_chart": _to_int(cells[3]),
            "peak_position": _to_int(cells[4]),
            "daily_streams": _to_int(cells[6]),
            "streams_7day": _to_int(cells[8]),
            "total_streams": _to_int(cells[10]),
        })
    return pd.DataFrame(records)


def get_audio_features(track_ids: list[str], batch_size: int = 40) -> pd.DataFrame:
    """Pide a ReccoBeats las audio features de una lista de IDs de Spotify."""
    results = []
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        resp = requests.get(FEATURES_URL, params={"ids": ",".join(batch)}, timeout=30)
        resp.raise_for_status()
        for item in resp.json().get("content", []):
            item["track_id"] = item["href"].rsplit("/", 1)[-1]
            results.append(item)
        time.sleep(0.3)  # no saturar la API
    features = pd.DataFrame(results)[["track_id", *FEATURES]]
    return features.drop_duplicates(subset=["track_id"])


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    today = date.today()

    charts = []
    for code, name in COUNTRIES.items():
        chart = get_chart(code)
        chart.insert(0, "country", name)
        chart.insert(1, "country_code", code)
        charts.append(chart)
        print(f"{name:<15} {len(chart)} canciones")
        time.sleep(0.5)
    charts = pd.concat(charts, ignore_index=True)

    unique_ids = charts["track_id"].unique().tolist()
    features = get_audio_features(unique_ids)
    print(f"\nCanciones únicas: {len(unique_ids)} | con audio features: {len(features)}")

    # 1) Formato largo: una fila por (país, canción). Solo canciones con audio features.
    long_df = charts.merge(features, on="track_id", how="inner")
    long_df.insert(0, "chart_date", today.isoformat())
    long_path = DATA_DIR / f"spotify_top200_countries_{today:%Y%m%d}.csv"
    long_df.to_csv(long_path, index=False)

    # 2) Una fila por canción: streams sumados en todos los países donde aparece.
    songs = (
        charts.groupby("track_id")
        .agg(
            artist=("artist", "first"),
            title=("title", "first"),
            n_countries=("country", "nunique"),
            best_rank=("rank", "min"),
            daily_streams=("daily_streams", "sum"),
            streams_7day=("streams_7day", "sum"),
            max_days_on_chart=("days_on_chart", "max"),
        )
        .reset_index()
        .merge(features, on="track_id", how="inner")
        .sort_values("daily_streams", ascending=False)
    )
    songs.insert(0, "chart_date", today.isoformat())
    songs_path = DATA_DIR / f"spotify_top200_songs_{today:%Y%m%d}.csv"
    songs.to_csv(songs_path, index=False)

    print(f"Guardado {long_path.name}: {len(long_df)} filas")
    print(f"Guardado {songs_path.name}: {len(songs)} filas")


if __name__ == "__main__":
    main()

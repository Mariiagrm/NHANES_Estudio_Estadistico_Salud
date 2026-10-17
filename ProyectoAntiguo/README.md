# Spotify Popularity Analysis (Linear Regression + Bootstrapping)

I put this project together to figure out which audio features (like danceability, energy, valence, etc.) actually drive a song's popularity on Spotify right now.

Instead of just fitting a standard OLS linear regression, I implemented a bootstrapping approach. Music data is super noisy, hits are massive outliers, and the data rarely fits strict homoscedasticity assumptions. Bootstrapping the regression gives us empirical confidence intervals for the coefficients, so we can see which features *consistently* matter without relying on perfect data distributions.

## Tech Stack

* **Python 3.10+**
* **Requests** (for pulling the daily charts and the audio features)
* **Pandas & NumPy** (data manipulation)
* **Statsmodels / Scikit-learn** (modeling)
* **Matplotlib / Seaborn** (for plotting the coefficient distributions)

## Where the data comes from

Since November 2024, the Spotify Web API no longer gives new apps access to `audio-features` or to editorial playlists like the Top 50 Global. That makes the classic `spotipy` approach a dead end, so the data comes from these sources instead:

* **[kworb.net](https://kworb.net/spotify/)**: daily mirrors of the official Spotify Top 200 charts per country, including daily streams, 7-day streams, days on chart and peak position.
* **[ReccoBeats API](https://reccobeats.com/)**: a free API (no key needed) that returns the same audio features Spotify used to provide, looked up by Spotify track ID.
* **[Spotify Tracks Dataset](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset)**: an older, larger dataset (~114k tracks across 114 genres) that still has the original Spotify `popularity` score (0-100). It's useful for comparison.

Popularity is measured with **daily streams** in the current-songs dataset, since the Spotify `popularity` score is no longer available. I use `log(daily_streams)` as the response variable because stream counts are heavily skewed.

## Getting Started

No API keys needed.

1. Clone the repo:
```bash
git clone https://github.com/Mariiagrm/Linear_Regression_Spotify_Songs.git
cd Linear_Regression_Spotify_Songs
```

2. Install the required libraries:
```bash
pip install -r requirements.txt
```

## How to use it

1. **`get_current_data.py`**: run this one first. It downloads today's Top 200 daily charts from 12 countries (Spain, US, France, UK, Germany, Italy, Mexico, Brazil, Argentina, Canada, Australia and the Netherlands). It then pulls the audio features for every song and saves two files to `data/`:
   * `spotify_top200_songs_<date>.csv` has **one row per unique song**, with streams summed across countries, `n_countries` and `best_rank`. This is the one to use for the regression.
   * `spotify_top200_countries_<date>.csv` has **one row per (country, song)**.

   To add or remove countries, edit the `COUNTRIES` dict at the top of the script.
2. **`get_data.py`** (optional): downloads and cleans the bigger Spotify Tracks Dataset into `data/spotify_tracks_clean.csv` (~90k unique songs).
3. **`analysis.ipynb`** *(work in progress)*: loads the CSV, fits the regression, runs $B=2000$ bootstrap iterations and plots the 95% confidence intervals for each audio feature.

### Variables

| Type | Columns |
|---|---|
| Response (y) | `daily_streams` (use the log), `streams_7day`, `best_rank` |
| Audio features (X) | `danceability`, `energy`, `valence`, `acousticness`, `instrumentalness`, `speechiness`, `liveness`, `loudness`, `tempo`, `key`, `mode` |
| Controls | `n_countries`, `max_days_on_chart` |

## Known Issues & To-Do

* [ ] **Missing audio features:** ReccoBeats doesn't have every song. The newest releases and local hits are often missing, so only about 54% of the chart songs make it into the dataset. This could bias the sample toward slightly older hits.
* [ ] **Selection bias:** every song in the charts is already a hit. The model explains what separates big hits from smaller ones, not what makes a song popular in the first place.
* [ ] **Country-level data:** in the per-country file, the same song shows up in several rows. If you use it, add country dummies and resample by song (cluster bootstrap) instead of by row.
* [ ] **Non-linear relationships:** the current model is strictly linear. I might add polynomial features later, since things like `tempo` probably have a "sweet spot" rather than a strictly linear relationship with popularity.
* [ ] Build the analysis notebook and clean up the histogram plots for the bootstrap distributions.

## License

MIT. Feel free to use this for your own classes or projects.

# spotify-language-playlist

Create a Spotify playlist from your liked songs filtered by language.

## How it works

The script fetches all your Spotify liked songs, detects the language of each
track from its title and artist names, and creates a new private playlist
containing only the tracks that match the language you specify.

## Prerequisites

- Python 3.10 or later
- A [Spotify developer application](https://developer.spotify.com/dashboard)
  with the redirect URI set to `http://127.0.0.1:8888/callback`

## Setup

1. **Clone the repo and install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials**

   Copy `.env.example` to `.env` and fill in your Spotify app credentials:

   ```bash
   cp .env.example .env
   ```

   Then edit `.env`:

   ```
   SPOTIPY_CLIENT_ID=<your client id>
   SPOTIPY_CLIENT_SECRET=<your client secret>
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

   > You can find your client ID and secret in the Spotify developer dashboard
   > under your application's settings.  Make sure the redirect URI you enter
   > there matches the one in `.env`.
   >
   > **Note:** Spotify accepts `http://` redirect URIs for loopback addresses
   > such as `127.0.0.1`.  See the
   > [Redirect URI guide](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
   > in the Spotify developer documentation for details.

## Usage

```bash
python -m spotify_language_playlist
```

The script will:

1. Open a browser window asking you to authorise the app (first run only).
2. Prompt you for a language (e.g. `Spanish`, `French`, `Japanese`).
3. Scan all your liked songs and detect their language.
4. Create a new private playlist named after the language containing every
   matched track.
5. Print a link to the new playlist.

You can type either a full language name (case-insensitive) or an
[ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) code
directly (e.g. `es`, `fr`, `ja`).

## Running the tests

```bash
pytest
```

## Notes

- Language is detected from the **track title and artist names**, which works
  well for most non-English languages.  Songs with very short or ambiguous
  titles may occasionally be misclassified.
- The created playlist is **private** by default.
- Running the script again for the same language will create a new playlist
  rather than updating the existing one.
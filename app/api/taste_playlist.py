"""Taste playlist route (docs/redesign.md A8b item 1).

HTTP adapter only; logic is ``intelligence.api.taste_playlist``. ``POST /api/playlists/taste`` with
``{"genre": "<value>"}`` writes a Navidrome playlist of up to 50 random songs of that genre from the
owner's library and answers its id. This is the one route that writes a playlist to Navidrome; it makes
no provider call and never logs the genre.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from intelligence.api.taste_playlist import PAGE, NoSongs, clean_genre, create_genre_playlist

router = APIRouter()


@router.post("/api/playlists/taste")
def make_taste_playlist(body: dict[str, Any], librarian=Depends(get_librarian)):
    genre = clean_genre(body.get("genre"))
    if genre is None:
        raise HTTPException(status_code=400, detail="genre must be a non-empty string of at most 100 characters")

    def songs_by_genre(name, offset):
        root = librarian.api_call("getSongsByGenre", genre=name, count=PAGE, offset=offset)
        return librarian.items(root.get("songsByGenre", {}).get("song"))

    def create_playlist(name, song_ids):
        root = librarian.api_call("createPlaylist", name=name, songId=song_ids)
        return str(root.get("playlist", {}).get("id") or "")

    try:
        result = create_genre_playlist(genre, songs_by_genre, create_playlist)
    except NoSongs:
        raise HTTPException(status_code=404, detail="No songs of that genre in the library.")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not create the playlist in Navidrome.")
    if not result["playlist_id"]:
        raise HTTPException(status_code=502, detail="Navidrome did not return a playlist id.")
    return result

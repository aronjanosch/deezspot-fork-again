#!/usr/bin/python3

from time import sleep
from datetime import datetime
from deezspot.deezloader.__utils__ import artist_sort
from requests import get as req_get
from deezspot.libutils.utils import convert_to_date
from deezspot.libutils.others_settings import header
from deezspot.exceptions import (
    NoDataApi,
    QuotaExceeded,
    TrackNotFound,
)
from deezspot.libutils.logging_utils import logger


class API:

    @classmethod
    def __init__(cls):
        cls.__api_link = "https://api.deezer.com/"
        cls.__cover = (
            "https://e-cdns-images.dzcdn.net/images/cover/%s/{}-000000-80-0-0.jpg"
        )
        cls.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    @classmethod
    def __get_api(cls, url, quota_exceeded=False):
        try:
            response = req_get(url, headers=cls.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get API data from {url}: {str(e)}")
            raise

    @classmethod
    def get_chart(cls, index=0):
        url = f"{cls.__api_link}chart/{index}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_track(cls, track_id):
        url = f"{cls.__api_link}track/{track_id}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_album(cls, album_id):
        url = f"{cls.__api_link}album/{album_id}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_playlist(cls, playlist_id):
        url = f"{cls.__api_link}playlist/{playlist_id}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_episode(cls, episode_id):
        url = f"{cls.__api_link}episode/{episode_id}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_artist(cls, ids):
        url = f"{cls.__api_link}artist/{ids}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_artist_top_tracks(cls, ids, limit=25):
        url = f"{cls.__api_link}artist/{ids}/top?limit={limit}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_artist_top_albums(cls, ids, limit=25):
        url = f"{cls.__api_link}artist/{ids}/albums?limit={limit}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_artist_related(cls, ids):
        url = f"{cls.__api_link}artist/{ids}/related"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_artist_radio(cls, ids):
        url = f"{cls.__api_link}artist/{ids}/radio"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def get_artist_top_playlists(cls, ids, limit=25):
        url = f"{cls.__api_link}artist/{ids}/playlists?limit={limit}"
        infos = cls.__get_api(url)

        return infos

    @classmethod
    def search(cls, query, limit=25):
        url = f"{cls.__api_link}search"
        params = {"q": query, "limit": limit}
        infos = cls.__get_api(url, params=params)

        if infos["total"] == 0:
            raise NoDataApi(query)

        return infos

    @classmethod
    def search_track(cls, query, limit=None):
        url = f"{cls.__api_link}search/track/?q={query}"

        # Add the limit parameter to the URL if it is provided
        if limit is not None:
            url += f"&limit={limit}"

        infos = cls.__get_api(url)

        if infos["total"] == 0:
            raise NoDataApi(query)

        return infos

    @classmethod
    def search_album(cls, query, limit=None):
        url = f"{cls.__api_link}search/album/?q={query}"

        # Add the limit parameter to the URL if it is provided
        if limit is not None:
            url += f"&limit={limit}"

        infos = cls.__get_api(url)

        if infos["total"] == 0:
            raise NoDataApi(query)

        return infos

    @classmethod
    def search_playlist(cls, query, limit=None):
        url = f"{cls.__api_link}search/playlist/?q={query}"

        # Add the limit parameter to the URL if it is provided
        if limit is not None:
            url += f"&limit={limit}"

        infos = cls.__get_api(url)

        if infos["total"] == 0:
            raise NoDataApi(query)

        return infos

    @classmethod
    def search_artist(cls, query, limit=None):
        url = f"{cls.__api_link}search/artist/?q={query}"

        # Add the limit parameter to the URL if it is provided
        if limit is not None:
            url += f"&limit={limit}"

        infos = cls.__get_api(url)

        if infos["total"] == 0:
            raise NoDataApi(query)

        return infos

    @classmethod
    def not_found(cls, song, title):
        try:
            data = cls.search_track(song)["data"]
        except NoDataApi:
            raise TrackNotFound(song)

        ids = None

        for track in data:
            if (track["title"] == title) or (title in track["title_short"]):
                ids = track["id"]
                break

        if not ids:
            raise TrackNotFound(song)

        return str(ids)

    @classmethod
    def get_img_url(cls, md5_image, size="1200x1200"):
        cover = cls.__cover.format(size)
        image_url = cover % md5_image

        return image_url

    @classmethod
    def choose_img(cls, md5_image, size="1200x1200"):
        image_url = cls.get_img_url(md5_image, size)
        image = req_get(image_url).content

        if len(image) == 13:
            image_url = cls.get_img_url("", size)
            image = req_get(image_url).content

        return image

    @classmethod
    def tracking(cls, ids, album=False) -> dict:
        song_metadata = {}
        json_track = cls.get_track(ids)

        if not album:
            album_ids = json_track["album"]["id"]
            album_json = cls.get_album(album_ids)
            genres = []

            if "genres" in album_json:
                for genre in album_json["genres"]["data"]:
                    genres.append(genre["name"])

            song_metadata["genre"] = "; ".join(genres)
            ar_album = []

            # Check if contributors field exists before accessing it
            if "contributors" in album_json:
                for contributor in album_json["contributors"]:
                    if contributor["role"] == "Main":
                        ar_album.append(contributor["name"])
            else:
                # If no contributors are found, use the main artist as a fallback
                if "artist" in json_track and "name" in json_track["artist"]:
                    ar_album.append(json_track["artist"]["name"])
                logger.info(
                    f"No contributors found for album {album_ids}, using artist as fallback"
                )

            song_metadata["ar_album"] = "; ".join(ar_album)
            song_metadata["album"] = album_json["title"]
            song_metadata["label"] = album_json.get("label", "Unknown")
            song_metadata["upc"] = album_json.get("upc", "Unknown")
            song_metadata["nb_tracks"] = album_json.get("nb_tracks", 1)

        song_metadata["music"] = json_track["title"]
        array = []

        # Check if contributors field exists in the track before accessing it
        if "contributors" in json_track:
            for contributor in json_track["contributors"]:
                if contributor["name"] != "":
                    array.append(contributor["name"])

        # Always add the main artist to ensure we have at least one artist
        array.append(json_track["artist"]["name"])

        song_metadata["artist"] = artist_sort(array)
        song_metadata["tracknum"] = json_track.get("track_position", 1)
        song_metadata["discnum"] = json_track.get("disk_number", 1)
        song_metadata["year"] = convert_to_date(
            json_track.get("release_date", "0000-00-00")
        )
        song_metadata["bpm"] = json_track.get("bpm", 0)
        song_metadata["duration"] = json_track.get("duration", 0)
        song_metadata["isrc"] = json_track.get("isrc", "")
        song_metadata["gain"] = json_track.get("gain", 0)

        return song_metadata

    @classmethod
    def tracking_album(cls, album_json):
        song_metadata: dict[str, list or str or int or datetime] = {
            "music": [],
            "artist": [],
            "tracknum": [],
            "discnum": [],
            "bpm": [],
            "duration": [],
            "isrc": [],
            "gain": [],
            "album": album_json["title"],
            "label": album_json.get("label", "Unknown"),
            "year": convert_to_date(album_json.get("release_date", "0000-00-00")),
            "upc": album_json.get("upc", "Unknown"),
            "nb_tracks": album_json.get("nb_tracks", 0),
        }

        genres = []

        if "genres" in album_json:
            for a in album_json["genres"]["data"]:
                genres.append(a["name"])

        song_metadata["genre"] = "; ".join(genres)
        ar_album = []

        # Check if contributors field exists before accessing it
        if "contributors" in album_json:
            for a in album_json["contributors"]:
                if a["role"] == "Main":
                    ar_album.append(a["name"])
        else:
            # If no contributors field, use the main artist as fallback
            if "artist" in album_json and "name" in album_json["artist"]:
                ar_album.append(album_json["artist"]["name"])
            logger.info(f"No contributors found for album, using artist as fallback")

        song_metadata["ar_album"] = "; ".join(ar_album)
        sm_items = song_metadata.items()

        for track in album_json["tracks"]["data"]:
            c_ids = track["id"]
            detas = cls.tracking(c_ids, album=True)

            for key, item in sm_items:
                if type(item) is list:
                    song_metadata[key].append(detas[key])

        return song_metadata

#!/usr/bin/python3

from base64 import b64encode
from mutagen.flac import FLAC, Picture
from mutagen.oggvorbis import OggVorbis
from deezspot.models import Track, Episode
import requests
import os
import logging

# Set up logging
logger = logging.getLogger("deezspot")


def request(url):
    response = requests.get(url)
    response.raise_for_status()
    return response


from mutagen.id3 import (
    ID3NoHeaderError,
    ID3,
    APIC,
    USLT,
    SYLT,
    COMM,
    TSRC,
    TRCK,
    TIT2,
    TLEN,
    TEXT,
    TCON,
    TALB,
    TBPM,
    TPE1,
    TYER,
    TDAT,
    TPOS,
    TPE2,
    TPUB,
    TCOP,
    TXXX,
    TCOM,
    IPLS,
)


def __write_flac(song, data):
    try:
        tag = FLAC(song)
        tag.delete()
        images = Picture()
        images.type = 3
        images.mime = "image/jpeg"

        # Handle image data
        if isinstance(data.get("image"), bytes):
            images.data = data["image"]
        elif isinstance(data.get("image"), str) and data["image"].startswith("http"):
            try:
                images.data = request(data["image"]).content
            except Exception as e:
                logger.warning(
                    f"Failed to download image from URL {data['image']}: {str(e)}"
                )
                images.data = b""
        else:
            images.data = b""

        tag.clear_pictures()
        tag.add_picture(images)

        # Add text metadata with validation
        metadata_fields = {
            "lyrics": data.get("lyric", ""),
            "artist": data.get("artist", ""),
            "title": data.get("music", ""),
            "date": (
                f"{data.get('year', '').year}/{data.get('year', '').month}/{data.get('year', '').day}"
                if hasattr(data.get("year", ""), "year")
                else ""
            ),
            "album": data.get("album", ""),
            "tracknumber": f"{data.get('tracknum', '')}",
            "discnumber": f"{data.get('discnum', '')}",
            "genre": data.get("genre", ""),
            "albumartist": data.get("ar_album", ""),
            "author": data.get("author", ""),
            "composer": data.get("composer", ""),
            "copyright": data.get("copyright", ""),
            "bpm": f"{data.get('bpm', '')}",
            "length": f"{int(data.get('duration', 0) * 1000)}",
            "organization": data.get("label", ""),
            "isrc": data.get("isrc", ""),
            "lyricist": data.get("lyricist", ""),
            "version": data.get("version", ""),
        }

        for field, value in metadata_fields.items():
            if value:  # Only add non-empty values
                tag[field] = str(value)

        tag.save()
    except Exception as e:
        logger.error(f"Error writing FLAC tags for {song}: {str(e)}")
        # Don't raise the exception to avoid crashing the download


def __write_mp3(song, data):
    try:
        try:
            audio = ID3(song)
            audio.delete()
        except ID3NoHeaderError:
            audio = ID3()

        # Add cover image if available
        if isinstance(data.get("image"), bytes) and data["image"]:
            audio.add(
                APIC(
                    mime="image/jpeg",
                    type=3,
                    desc="album front cover",
                    data=data["image"],
                )
            )

        audio.add(
            COMM(lang="eng", desc="my comment", text="DO NOT USE FOR YOUR OWN EARNING")
        )

        # Add lyrics if available
        if "lyric" in data and data["lyric"]:
            audio.add(USLT(text=data["lyric"]))

        # Add synchronized lyrics if available
        if "lyric_sync" in data and data["lyric_sync"]:
            audio.add(
                SYLT(type=1, format=2, desc="sync lyric song", text=data["lyric_sync"])
            )

        # Add other metadata fields with validation
        if "isrc" in data and data["isrc"]:
            audio.add(TSRC(text=data["isrc"]))

        if "tracknum" in data and "nb_tracks" in data:
            audio.add(TRCK(text=f"{data['tracknum']}/{data['nb_tracks']}"))
        elif "tracknum" in data:
            audio.add(TRCK(text=f"{data['tracknum']}"))

        if "music" in data and data["music"]:
            audio.add(TIT2(text=data["music"]))

        if "duration" in data:
            audio.add(TLEN(text=f"{data['duration']}"))

        if "lyricist" in data and data["lyricist"]:
            audio.add(TEXT(text=data["lyricist"]))

        if "genre" in data and data["genre"]:
            audio.add(TCON(text=data["genre"]))

        if "album" in data and data["album"]:
            audio.add(TALB(text=data["album"]))

        if "bpm" in data and data["bpm"]:
            audio.add(TBPM(text=f"{data['bpm']}"))

        if "artist" in data and data["artist"]:
            audio.add(TPE1(text=data["artist"]))

        if "year" in data and hasattr(data["year"], "year"):
            audio.add(TYER(text=f"{data['year'].year}"))
            audio.add(TDAT(text=f"{data['year'].day}{data['year'].month}"))

        if "discnum" in data:
            audio.add(TPOS(text=f"{data['discnum']}/{data['discnum']}"))

        if "ar_album" in data and data["ar_album"]:
            audio.add(TPE2(text=data["ar_album"]))

        if "label" in data and data["label"]:
            audio.add(TPUB(text=data["label"]))

        if "copyright" in data and data["copyright"]:
            audio.add(TCOP(text=data["copyright"]))

        if "gain" in data:
            audio.add(TXXX(desc="REPLAYGAIN_TRACK_GAIN", text=f"{data['gain']}"))

        if "composer" in data and data["composer"]:
            audio.add(TCOM(text=data["composer"]))

        if "author" in data and data["author"]:
            audio.add(IPLS(people=[data["author"]]))

        audio.save(song, v2_version=3)
    except Exception as e:
        logger.error(f"Error writing MP3 tags for {song}: {str(e)}")
        # Don't raise the exception to avoid crashing the download


def __write_ogg(song, song_metadata):
    try:
        audio = OggVorbis(song)
        audio.delete()

        # Standard Vorbis comment fields mapping
        field_mapping = {
            "music": "title",
            "artist": "artist",
            "album": "album",
            "tracknum": "tracknumber",
            "discnum": "discnumber",
            "year": "date",
            "genre": "genre",
            "isrc": "isrc",
            "description": "description",
            "ar_album": "albumartist",
            "composer": "composer",
            "copyright": "copyright",
            "bpm": "bpm",
            "lyricist": "lyricist",
            "version": "version",
        }

        # Add standard text metadata
        for source_key, vorbis_key in field_mapping.items():
            if source_key in song_metadata and song_metadata[source_key] is not None:
                value = song_metadata[source_key]

                # Special handling for date field
                if vorbis_key == "date":
                    # Convert datetime object to YYYY-MM-DD string format
                    if hasattr(value, "strftime"):
                        value = value.strftime("%Y-%m-%d")
                    # Handle string timestamps if necessary
                    elif isinstance(value, str) and " " in value:
                        value = value.split()[0]

                # Skip "Unknown" BPM values or other non-numeric BPM values
                if vorbis_key == "bpm" and (
                    value == "Unknown"
                    or not isinstance(value, (int, float))
                    and not str(value).isdigit()
                ):
                    continue

                audio[vorbis_key] = [str(value)]

        # Add lyrics if present
        if "lyric" in song_metadata and song_metadata["lyric"]:
            audio["lyrics"] = [str(song_metadata["lyric"])]

        # Handle cover art
        if "image" in song_metadata and song_metadata["image"]:
            try:
                image = Picture()
                image.type = 3  # Front cover
                image.mime = "image/jpeg"
                image.desc = "Cover"

                if isinstance(song_metadata["image"], bytes):
                    image.data = song_metadata["image"]
                elif isinstance(song_metadata["image"], str) and song_metadata[
                    "image"
                ].startswith("http"):
                    try:
                        image.data = request(song_metadata["image"]).content
                    except Exception as img_e:
                        logger.warning(f"Failed to download image: {str(img_e)}")
                        image.data = b""
                else:
                    image.data = b""

                # Encode using base64 as required by Vorbis spec
                if image.data:
                    audio["metadata_block_picture"] = [
                        b64encode(image.write()).decode("utf-8")
                    ]
            except Exception as e:
                logger.warning(f"Error adding cover art: {e}")

        # Additional validation for numeric fields - exclude BPM since we already handled it
        numeric_fields = ["tracknumber", "discnumber"]
        for field in numeric_fields:
            if field in audio:
                try:
                    int(audio[field][0])
                except ValueError:
                    logger.warning(f"Warning: Invalid numeric value for {field}")
                    del audio[field]

        audio.save()
    except Exception as e:
        logger.error(f"Error writing OGG tags for {song}: {str(e)}")
        # Don't raise the exception to avoid crashing the download


def write_tags(media):
    """
    Write metadata tags to the audio file.

    Args:
        media: Track or Episode object containing metadata
    """
    try:
        # Determine the file path based on media type
        if isinstance(media, Track):
            song = media.song_path
        elif isinstance(media, Episode):
            song = media.episode_path
        else:
            logger.warning(f"Unsupported media type: {type(media).__name__}")
            return

        # Skip if song path is None or file doesn't exist
        if not song:
            logger.warning("Media has no path set, skipping tag writing")
            return

        if not os.path.isfile(song):
            logger.warning(f"File does not exist: {song}")
            return

        # Get the metadata and format
        song_metadata = media.tags
        f_format = media.file_format

        # Apply the appropriate tag writer
        if f_format == ".flac":
            __write_flac(song, song_metadata)
        elif f_format == ".ogg":
            __write_ogg(song, song_metadata)
        else:
            __write_mp3(song, song_metadata)

        logger.debug(f"Successfully wrote tags for {song}")

    except Exception as e:
        logger.error(f"Error writing tags: {str(e)}")
        # We don't re-raise the exception to avoid crashing the download process


def check_track(media):
    """
    Check if a track's metadata and file are valid.

    Args:
        media: Track or Episode object to check

    Returns:
        bool: True if track exists and has been previously tagged
    """
    try:
        # Determine the file path based on media type
        if isinstance(media, Track):
            file_path = media.song_path
        elif isinstance(media, Episode):
            file_path = media.episode_path
        else:
            logger.warning(f"Unsupported media type for check: {type(media).__name__}")
            return False

        # Check if file exists
        if not file_path or not os.path.isfile(file_path):
            return False

        # Try to read metadata based on file type
        if file_path.lower().endswith(".mp3"):
            try:
                from mutagen.mp3 import MP3

                audio = MP3(file_path)
                # Check if we have some basic tags
                return bool(audio) and len(audio) > 0
            except Exception:
                return False
        elif file_path.lower().endswith(".flac"):
            try:
                audio = FLAC(file_path)
                return bool(audio) and len(audio) > 0
            except Exception:
                return False
        elif file_path.lower().endswith(".ogg"):
            try:
                audio = OggVorbis(file_path)
                return bool(audio) and len(audio) > 0
            except Exception:
                return False
        elif file_path.lower().endswith((".m4a", ".mp4")):
            try:
                from mutagen.mp4 import MP4

                audio = MP4(file_path)
                return bool(audio) and len(audio) > 0
            except Exception:
                return False
        else:
            try:
                # Generic attempt for other formats
                from mutagen import File

                audio = File(file_path)
                return bool(audio) and len(audio) > 0
            except Exception:
                return False

    except Exception as e:
        logger.error(f"Error checking track: {str(e)}")
        return False

    return False

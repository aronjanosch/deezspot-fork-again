#!/usr/bin/env python3

import os
import json
import logging
import argparse
import traceback
import sys
from pathlib import Path

# Configure more verbose logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Ensure output goes to stdout
        logging.FileHandler("deezspot_test.log"),  # Also log to a file
    ],
)
logger = logging.getLogger("deezspot_test")


def load_deezer_credentials(username=None):
    """Load Deezer credentials from the credentials file"""
    try:
        base_path = Path("creds/deezer")
        logger.debug(f"Looking for Deezer credentials in {base_path.absolute()}")

        # If username is specified, use that user's credentials
        if username:
            cred_file = base_path / username / "credentials.json"
        else:
            # Otherwise find the first available credentials file
            user_dirs = list(base_path.glob("*/credentials.json"))
            if not user_dirs:
                logger.error(f"No Deezer credentials found in {base_path.absolute()}")
                return None
            cred_file = user_dirs[0]
            username = cred_file.parent.name

        logger.debug(f"Using credentials file: {cred_file.absolute()}")

        if not cred_file.exists():
            logger.error(
                f"Credentials file for {username} does not exist: {cred_file.absolute()}"
            )
            return None

        with open(cred_file, "r") as f:
            credentials = json.load(f)

        if "arl" not in credentials:
            logger.error(
                f"ARL token not found in credentials file: {cred_file.absolute()}"
            )
            return None

        logger.info(f"Successfully loaded Deezer credentials for user: {username}")
        # Show a masked version of the ARL token for debugging
        arl = credentials["arl"]
        masked_arl = (
            arl[:4] + "*" * (len(arl) - 8) + arl[-4:] if len(arl) > 8 else "****"
        )
        logger.debug(f"ARL token: {masked_arl}")
        return credentials["arl"]
    except Exception as e:
        logger.error(f"Error loading Deezer credentials: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def load_spotify_api_credentials():
    """Load Spotify API credentials (for use with spotipy)"""
    try:
        # Try to load from environment variables first
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        env_source = None

        if client_id and client_secret:
            env_source = "environment variables"
            logger.debug("Found Spotify API credentials in environment variables")

        # If not in environment, try to load from a config file
        if not client_id or not client_secret:
            config_paths = [
                Path("creds/spotify_api.json"),
                Path("spotify_api.json"),
                Path(os.path.expanduser("~/.spotify_api.json")),
            ]

            for config_file in config_paths:
                if config_file.exists():
                    logger.debug(
                        f"Found Spotify API config file: {config_file.absolute()}"
                    )
                    with open(config_file, "r") as f:
                        config = json.load(f)
                        client_id = config.get("client_id")
                        client_secret = config.get("client_secret")
                        if client_id and client_secret:
                            env_source = str(config_file)
                            break

        if client_id and client_secret:
            # Show masked versions of the credentials for debugging
            masked_id = (
                client_id[:4] + "*" * (len(client_id) - 8) + client_id[-4:]
                if len(client_id) > 8
                else "****"
            )
            masked_secret = (
                client_secret[:4] + "*" * (len(client_secret) - 8) + client_secret[-4:]
                if len(client_secret) > 8
                else "****"
            )
            logger.info(
                f"Successfully loaded Spotify API credentials from {env_source}"
            )
            logger.debug(f"Spotify Client ID: {masked_id}")
            logger.debug(f"Spotify Client Secret: {masked_secret}")
            return client_id, client_secret
        else:
            logger.warning(
                "Spotify API credentials not found. Some features may not work."
            )
            return None, None
    except Exception as e:
        logger.error(f"Error loading Spotify API credentials: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None


def find_spotify_credentials_file():
    """Find the Spotify credentials.json file"""
    try:
        base_path = Path("creds/spotify")
        logger.debug(f"Looking for Spotify credentials in {base_path.absolute()}")

        # Find the first available Spotify credentials file
        user_dirs = list(base_path.glob("*/credentials.json"))
        if user_dirs:
            cred_file = user_dirs[0]
            username = cred_file.parent.name
            logger.info(
                f"Found Spotify credentials for user: {username} at {cred_file.absolute()}"
            )
            return str(cred_file)
        else:
            logger.warning(f"No Spotify credentials found in {base_path.absolute()}")
            return None
    except Exception as e:
        logger.error(f"Error finding Spotify credentials: {str(e)}")
        return None


def test_playlist_download(
    arl_token,
    playlist_url,
    output_dir="test_output",
    convert_to=None,
    spotify_client_id=None,
    spotify_client_secret=None,
):
    """
    Test downloading a playlist, specifically testing our fixes for playlist resiliency
    """
    from deezspot.deezloader import DeeLogin
    from deezspot.easy_spoty import Spo  # Import Spo class directly

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {os.path.abspath(output_dir)}")

    # Initialize Spotify API first
    if spotify_client_id and spotify_client_secret:
        logger.info("Initializing Spotify API with client credentials")
        try:
            Spo.__init__(
                client_id=spotify_client_id, client_secret=spotify_client_secret
            )
            logger.info("Spotify API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify API: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    else:
        logger.warning(
            "Spotify client credentials not provided. Some features may not work."
        )

    # Initialize the DeeLogin downloader
    logger.info(f"Initializing DeeLogin with ARL token")
    try:
        dl = DeeLogin(
            arl=arl_token,
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
        )
        logger.info("DeeLogin initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DeeLogin: {str(e)}")
        logger.error(traceback.format_exc())
        return None

    # Test downloading a playlist
    logger.info(f"Starting playlist download: {playlist_url}")
    try:
        # Print some info about the parameters
        logger.debug(f"Download parameters:")
        logger.debug(f"  Output directory: {output_dir}")
        logger.debug(f"  Quality: MP3_320")
        logger.debug(f"  Recursive quality: True")
        logger.debug(f"  Recursive download: True")
        logger.debug(f"  Convert to: {convert_to}")

        playlist = dl.download_playlistspo(
            playlist_url,
            output_dir=output_dir,
            quality_download="MP3_320",
            recursive_quality=True,
            recursive_download=True,
            not_interface=True,
            make_zip=True,
            convert_to=convert_to,
        )

        # Check results
        if not playlist:
            logger.error("Download failed - no playlist object returned")
            return None

        if not hasattr(playlist, "tracks"):
            logger.error("Download failed - playlist has no tracks attribute")
            return None

        total_tracks = len(playlist.tracks)
        successful_tracks = sum(1 for track in playlist.tracks if track.success)

        logger.info(
            f"Playlist download completed. Total tracks: {total_tracks}, Successfully downloaded: {successful_tracks}"
        )

        # Report on failed tracks
        if hasattr(playlist, "failed_track_errors") and playlist.failed_track_errors:
            logger.info(f"Failed tracks: {len(playlist.failed_track_errors)}")
            for error in playlist.failed_track_errors:
                logger.info(f"  - {error}")

        # List files in the output directory
        logger.info(f"Files in output directory:")
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                logger.info(f"  {os.path.join(root, file)}")

        return playlist
    except Exception as e:
        logger.error(f"Playlist download failed: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def test_tagging_resilience(arl_token, track_url, output_dir="test_output"):
    """
    Test the tagging system's resilience to issues
    """
    from deezspot.deezloader import DeeLogin
    from deezspot.__taggers__ import write_tags
    from deezspot.models.track import Track

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the downloader
    logger.info(f"Initializing DeeLogin with ARL token")
    try:
        dl = DeeLogin(arl=arl_token)
        logger.info("DeeLogin initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DeeLogin: {str(e)}")
        logger.error(traceback.format_exc())
        return None

    # First download a track normally to have something to work with
    logger.info(f"Downloading track: {track_url}")
    try:
        track = dl.download_trackdee(
            track_url, output_dir=output_dir, quality_download="MP3_320"
        )

        if not track or not track.success or not track.song_path:
            logger.error(f"Failed to download test track. Skipping tagging tests.")
            return None

        logger.info(f"Successfully downloaded track to {track.song_path}")
    except Exception as e:
        logger.error(f"Failed to download test track: {str(e)}")
        logger.error(traceback.format_exc())
        return None

    # Test 1: Modify the track to have an invalid path and verify tagging doesn't crash
    logger.info("Testing tagging with non-existent file path")
    track_copy = Track(
        track.tags, "/non/existent/path.mp3", ".mp3", "320", track.link, track.ids
    )
    try:
        write_tags(track_copy)
        logger.info("  - Pass: Tagging with non-existent path did not crash")
    except Exception as e:
        logger.error(f"  - Fail: Tagging with non-existent path crashed: {str(e)}")
        logger.error(traceback.format_exc())

    # Test 2: Modify the track to have invalid metadata and verify tagging doesn't crash
    logger.info("Testing tagging with invalid metadata")
    track_copy = Track({}, track.song_path, ".mp3", "320", track.link, track.ids)
    try:
        write_tags(track_copy)
        logger.info("  - Pass: Tagging with empty metadata did not crash")
    except Exception as e:
        logger.error(f"  - Fail: Tagging with empty metadata crashed: {str(e)}")
        logger.error(traceback.format_exc())

    return track


def main():
    parser = argparse.ArgumentParser(description="Test deezspot library fixes")
    parser.add_argument("--deezer-user", help="Deezer username to use credentials for")
    parser.add_argument(
        "--spotify-user", help="Spotify username to use credentials for"
    )
    parser.add_argument(
        "--output-dir", default="test_output", help="Output directory for downloads"
    )
    parser.add_argument("--playlist", help="URL of a playlist to test downloading")
    parser.add_argument(
        "--track", help="URL of a track to test downloading and tagging"
    )
    parser.add_argument(
        "--spotify-track", help="URL of a Spotify track to test conversion"
    )
    parser.add_argument("--convert-to", help="Test conversion (e.g., MP3_320, FLAC)")
    parser.add_argument(
        "--spotify-direct", action="store_true", help="Test direct Spotify download"
    )
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set log level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Print system information for debugging
    logger.info("Starting deezspot tests")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

    # Check for required directories
    if not os.path.exists("creds"):
        logger.error("Error: 'creds' directory not found")
        return 1

    if not os.path.exists("creds/deezer"):
        logger.error("Error: 'creds/deezer' directory not found")
        return 1

    if not os.path.exists("creds/spotify"):
        logger.warning("Warning: 'creds/spotify' directory not found")

    # Load credentials
    deezer_arl = load_deezer_credentials(args.deezer_user)
    if not deezer_arl:
        logger.error("Deezer ARL token not loaded. Please check credentials.")
        return 1

    # Load Spotify API credentials
    spotify_client_id, spotify_client_secret = load_spotify_api_credentials()
    if not spotify_client_id or not spotify_client_secret:
        logger.warning(
            "Spotify API credentials not loaded. Some features may not work."
        )

    # Find Spotify credentials file for direct download
    spotify_creds_path = find_spotify_credentials_file()

    # Create output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Using output directory: {os.path.abspath(output_dir)}")

    # Run tests based on arguments
    test_count = 0
    passed_count = 0

    if args.track or args.test_all:
        test_count += 1
        track_url = (
            args.track or "https://open.spotify.com/track/6GOOcBV0wLoHrH5D9AWA32"
        )  # Default: Daft Punk - Harder Better Faster Stronger
        logger.info(f"========== TESTING TAGGING RESILIENCE ==========")
        result = test_tagging_resilience(deezer_arl, track_url, output_dir)
        if result:
            passed_count += 1
            logger.info("✅ Tagging resilience test passed")
        else:
            logger.error("❌ Tagging resilience test failed")

    if args.playlist or args.test_all:
        test_count += 1
        playlist_url = (
            args.playlist or "https://open.spotify.com/playlist/2uZ5JD9vUXI9haI8LcMgeP"
        )  # Spotify Top 50 Global
        logger.info(f"========== TESTING PLAYLIST DOWNLOAD ==========")
        result = test_playlist_download(
            deezer_arl,
            playlist_url,
            output_dir,
            args.convert_to,
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
        )
        if result:
            passed_count += 1
            logger.info("✅ Playlist download test passed")
        else:
            logger.error("❌ Playlist download test failed")

    # Print summary
    logger.info(f"=== Test Summary ===")
    logger.info(f"Tests run: {test_count}")
    logger.info(f"Tests passed: {passed_count}")
    logger.info(f"Tests failed: {test_count - passed_count}")

    if test_count == 0:
        logger.warning(
            "No tests were run! Use --test-all or specify specific tests to run."
        )
        return 1

    return 0 if passed_count == test_count else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

#!/usr/bin/env python3
"""
YouTube Subscription Analyzer

This script analyzes your YouTube channel subscriptions and identifies which channels
you haven't watched in over one year based on your viewing history.
"""

import os
import pickle
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube API scopes required for reading subscriptions and watch history
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def get_authenticated_service():
    """
    Authenticate with YouTube API and return the service object.
    
    Returns:
        Resource: An authorized YouTube API service instance.
    """
    creds = None
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json file not found. Please download it from "
                    "Google Cloud Console. See README for instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def get_all_subscriptions(youtube) -> List[Dict]:
    """
    Fetch all channel subscriptions for the authenticated user.
    
    Args:
        youtube: Authenticated YouTube API service instance.
        
    Returns:
        List of subscription objects containing channel information.
    """
    print("Fetching your YouTube subscriptions...")
    subscriptions = []
    next_page_token = None
    
    try:
        while True:
            request = youtube.subscriptions().list(
                part='snippet',
                mine=True,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            subscriptions.extend(response.get('items', []))
            next_page_token = response.get('nextPageToken')
            
            print(f"  Fetched {len(subscriptions)} subscriptions so far...")
            
            if not next_page_token:
                break
                
    except HttpError as e:
        print(f"An error occurred while fetching subscriptions: {e}")
        return []
    
    print(f"Total subscriptions found: {len(subscriptions)}")
    return subscriptions

def load_watch_history_from_file(file_path: str, cutoff_date: datetime) -> Dict[str, datetime]:
    """
    Load watch history from a Google Takeout JSON file.
    
    Args:
        file_path: Path to the watch-history.json file from Google Takeout.
        cutoff_date: The date to look back from (e.g., 1 year ago).
        
    Returns:
        Dictionary mapping channel IDs to their most recent view date.
    """
    print(f"\nLoading watch history from file: {file_path}")
    print(f"Looking for videos watched since: {cutoff_date.strftime('%Y-%m-%d')}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Watch history file not found: {file_path}\n\n"
            "Please download your YouTube watch history:\n"
            "  1. Go to https://takeout.google.com\n"
            "  2. Deselect all, then select only 'YouTube and YouTube Music'\n"
            "  3. Click 'All YouTube data included', then deselect all\n"
            "  4. Select only 'history'\n"
            "  5. Click 'Next step' and create export\n"
            "  6. Download and extract the archive\n"
            "  7. Place 'watch-history.json' in this directory"
        )
    
    channel_last_watched = defaultdict(lambda: None)
    videos_checked = 0
    videos_in_timeframe = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            watch_history = json.load(f)
        
        print(f"Loaded {len(watch_history)} entries from watch history file")
        
        for entry in watch_history:
            videos_checked += 1
            
            # Google Takeout format uses 'time' field
            time_str = entry.get('time')
            if not time_str:
                continue
            
            # Parse the timestamp (format: 2024-12-31T12:34:56.789Z)
            try:
                # Handle different possible timestamp formats
                time_str = time_str.replace('+00:00', 'Z')
                if '.' in time_str:
                    # Has milliseconds
                    watched_at = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                else:
                    # No milliseconds
                    watched_at = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                # Try alternate formats
                try:
                    watched_at = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    watched_at = watched_at.replace(tzinfo=None)  # Make naive
                except:
                    continue
            
            # Only process videos within our timeframe
            if watched_at < cutoff_date:
                continue
            
            videos_in_timeframe += 1
            
            # Extract channel information
            # Google Takeout format: "titleUrl" contains the video URL
            title_url = entry.get('titleUrl', '')
            
            # The subtitles array contains channel info
            subtitles = entry.get('subtitles', [])
            channel_url = None
            channel_name = None
            
            for subtitle in subtitles:
                if 'url' in subtitle:
                    channel_url = subtitle['url']
                    channel_name = subtitle.get('name', '')
                    break
            
            if channel_url:
                # Extract channel ID from URL
                # Format: https://www.youtube.com/channel/CHANNEL_ID
                # or: https://www.youtube.com/@username
                if '/channel/' in channel_url:
                    channel_id = channel_url.split('/channel/')[-1].strip()
                elif '/@' in channel_url:
                    # For @username format, we'll use the username as identifier
                    # (we'll need to look it up via API later if needed)
                    channel_id = channel_url.split('/@')[-1].strip()
                else:
                    continue
                
                # Update the last watched date for this channel
                if channel_last_watched[channel_id] is None or watched_at > channel_last_watched[channel_id]:
                    channel_last_watched[channel_id] = watched_at
            
            if videos_checked % 1000 == 0:
                print(f"  Processed {videos_checked:,} entries... ({videos_in_timeframe:,} in timeframe)")
        
        print(f"\nProcessing complete:")
        print(f"  Total entries in file: {videos_checked:,}")
        print(f"  Videos watched since cutoff: {videos_in_timeframe:,}")
        print(f"  Unique channels found: {len(channel_last_watched):,}")
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file format: {e}")
    except Exception as e:
        raise Exception(f"Error reading watch history file: {e}")
    
    return dict(channel_last_watched)


def resolve_channel_handles(youtube, channel_identifiers: List[str]) -> Dict[str, str]:
    """
    Resolve @username handles to channel IDs using the YouTube API.
    
    Args:
        youtube: Authenticated YouTube API service instance.
        channel_identifiers: List of channel IDs or @username handles.
        
    Returns:
        Dictionary mapping original identifier to channel ID.
    """
    resolved = {}
    handles_to_resolve = []
    
    for identifier in channel_identifiers:
        if identifier.startswith('@') or not identifier.startswith('UC'):
            handles_to_resolve.append(identifier)
        else:
            resolved[identifier] = identifier  # Already a channel ID
    
    if not handles_to_resolve:
        return resolved
    
    print(f"\nResolving {len(handles_to_resolve)} channel handles to IDs...")
    
    for handle in handles_to_resolve:
        try:
            # Search for the channel by handle
            search_query = handle.replace('@', '')
            request = youtube.search().list(
                part='snippet',
                q=search_query,
                type='channel',
                maxResults=1
            )
            response = request.execute()
            
            items = response.get('items', [])
            if items:
                channel_id = items[0]['id']['channelId']
                resolved[handle] = channel_id
            else:
                resolved[handle] = handle  # Keep original if not found
                
        except HttpError:
            resolved[handle] = handle  # Keep original if lookup fails
    
    print(f"  Resolved {len([v for k, v in resolved.items() if k != v])} handles")
    
    return resolved

def analyze_subscriptions(subscriptions: List[Dict], watch_history: Dict[str, datetime], 
                         cutoff_date: datetime) -> Tuple[List[Dict], List[Dict]]:
    """
    Analyze subscriptions to identify channels not watched in over a year.
    
    Args:
        subscriptions: List of subscription objects.
        watch_history: Dictionary mapping channel IDs to last watch dates.
        cutoff_date: The date threshold (1 year ago).
        
    Returns:
        Tuple of (unwatched_channels, watched_channels).
    """
    unwatched = []
    watched = []
    
    for sub in subscriptions:
        channel_id = sub['snippet']['resourceId']['channelId']
        channel_title = sub['snippet']['title']
        
        last_watched = watch_history.get(channel_id)
        
        if last_watched is None:
            # Never watched (or no record found)
            unwatched.append({
                'title': channel_title,
                'channel_id': channel_id,
                'last_watched': None,
                'reason': 'No viewing activity found'
            })
        elif last_watched < cutoff_date:
            # Watched, but not in the last year
            unwatched.append({
                'title': channel_title,
                'channel_id': channel_id,
                'last_watched': last_watched,
                'reason': f'Last watched {last_watched.strftime("%Y-%m-%d")}'
            })
        else:
            # Watched within the last year
            watched.append({
                'title': channel_title,
                'channel_id': channel_id,
                'last_watched': last_watched
            })
    
    return unwatched, watched

def print_results(unwatched: List[Dict], watched: List[Dict], total: int):
    """
    Print the analysis results in a readable format.
    
    Args:
        unwatched: List of channels not watched in over a year.
        watched: List of channels watched in the last year.
        total: Total number of subscriptions.
    """
    print("\n" + "=" * 80)
    print("YOUTUBE SUBSCRIPTION ANALYSIS RESULTS")
    print("=" * 80)
    
    print(f"\nTotal Subscriptions: {total}")
    print(f"Watched in last year: {len(watched)}")
    print(f"NOT watched in last year: {len(unwatched)}")
    
    if unwatched:
        print("\n" + "-" * 80)
        print("CHANNELS NOT WATCHED IN OVER ONE YEAR:")
        print("-" * 80)
        
        for i, channel in enumerate(unwatched, 1):
            print(f"\n{i}. {channel['title']}")
            print(f"   Channel ID: {channel['channel_id']}")
            print(f"   Status: {channel['reason']}")
            print(f"   URL: https://www.youtube.com/channel/{channel['channel_id']}")
    else:
        print("\nGreat! You've watched videos from all your subscribed channels in the last year.")
    
    print("\n" + "=" * 80)

def save_results_to_file(unwatched: List[Dict], watched: List[Dict]):
    """
    Save analysis results to a text file for future reference.
    
    Args:
        unwatched: List of channels not watched in over a year.
        watched: List of channels watched in the last year.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'youtube_subscription_analysis_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("YOUTUBE SUBSCRIPTION ANALYSIS RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total Subscriptions: {len(unwatched) + len(watched)}\n")
        f.write(f"Watched in last year: {len(watched)}\n")
        f.write(f"NOT watched in last year: {len(unwatched)}\n\n")
        
        if unwatched:
            f.write("-" * 80 + "\n")
            f.write("CHANNELS NOT WATCHED IN OVER ONE YEAR:\n")
            f.write("-" * 80 + "\n\n")
            
            for i, channel in enumerate(unwatched, 1):
                f.write(f"{i}. {channel['title']}\n")
                f.write(f"   Channel ID: {channel['channel_id']}\n")
                f.write(f"   Status: {channel['reason']}\n")
                f.write(f"   URL: https://www.youtube.com/channel/{channel['channel_id']}\n\n")
        
        if watched:
            f.write("\n" + "-" * 80 + "\n")
            f.write("CHANNELS WATCHED IN THE LAST YEAR:\n")
            f.write("-" * 80 + "\n\n")
            
            for i, channel in enumerate(watched, 1):
                f.write(f"{i}. {channel['title']}\n")
                f.write(f"   Last watched: {channel['last_watched'].strftime('%Y-%m-%d')}\n\n")
    
    print(f"\nResults saved to: {filename}")

def main():
    """
    Main function to orchestrate the YouTube subscription analysis.
    """
    print("=" * 80)
    print("YOUTUBE SUBSCRIPTION ANALYZER")
    print("=" * 80)
    print("\nThis script analyzes which YouTube subscriptions you HAVEN'T watched in a year.")
    print("It uses your Google Takeout watch history data for accurate results.")
    print()
    
    # Check for watch history file
    watch_history_file = 'watch-history.json'
    if not os.path.exists(watch_history_file):
        print("ERROR: watch-history.json not found!")
        print("\nTo get your watch history:")
        print("  1. Go to https://takeout.google.com")
        print("  2. Deselect all, then select only 'YouTube and YouTube Music'")
        print("  3. Click 'All YouTube data included', then deselect all")
        print("  4. Select only 'history'")
        print("  5. Click 'Next step', choose file type and delivery method")
        print("  6. Click 'Create export' and wait for email notification")
        print("  7. Download and extract the archive")
        print("  8. Place 'watch-history.json' in this directory")
        print(f"\nExpected location: {os.path.abspath(watch_history_file)}")
        return
    
    try:
        # Authenticate with YouTube API (for subscriptions)
        youtube = get_authenticated_service()
        
        # Define cutoff date (1 year ago from today)
        cutoff_date = datetime.now() - timedelta(days=365)
        
        # Fetch all subscriptions
        subscriptions = get_all_subscriptions(youtube)
        
        if not subscriptions:
            print("No subscriptions found or unable to fetch subscriptions.")
            return
        
        # Load watch history from file
        watch_history = load_watch_history_from_file(watch_history_file, cutoff_date)
        
        # Resolve any @username handles to channel IDs
        if watch_history:
            handles = [ch_id for ch_id in watch_history.keys() if ch_id.startswith('@') or not ch_id.startswith('UC')]
            if handles:
                resolved = resolve_channel_handles(youtube, handles)
                # Update watch_history with resolved IDs
                new_history = {}
                for ch_id, date in watch_history.items():
                    resolved_id = resolved.get(ch_id, ch_id)
                    if resolved_id in new_history:
                        new_history[resolved_id] = max(new_history[resolved_id], date)
                    else:
                        new_history[resolved_id] = date
                watch_history = new_history
        
        # Analyze subscriptions
        unwatched, watched = analyze_subscriptions(subscriptions, watch_history, cutoff_date)
        
        # Print results
        print_results(unwatched, watched, len(subscriptions))
        
        # Save results to file
        save_results_to_file(unwatched, watched)
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

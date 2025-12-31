#!/usr/bin/env python3
"""
YouTube Subscription Analyzer

This script analyzes your YouTube channel subscriptions and identifies which channels
you haven't watched in over one year based on your viewing history.
"""

import os
import pickle
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Set, Tuple

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

def get_watch_history(youtube, cutoff_date: datetime) -> Dict[str, datetime]:
    """
    Fetch the user's watch history and track the most recent view for each channel.
    
    Args:
        youtube: Authenticated YouTube API service instance.
        cutoff_date: The date to look back from (e.g., 1 year ago).
        
    Returns:
        Dictionary mapping channel IDs to their most recent view date.
    """
    print(f"\nFetching your watch history (looking back to {cutoff_date.strftime('%Y-%m-%d')})...")
    channel_last_watched = defaultdict(lambda: None)
    next_page_token = None
    videos_checked = 0
    
    try:
        # Note: YouTube's myRating API doesn't provide full watch history
        # We'll use the activity API to get watched videos
        while True:
            request = youtube.activities().list(
                part='snippet,contentDetails',
                mine=True,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            items = response.get('items', [])
            
            for item in items:
                videos_checked += 1
                
                # Get the published date of the activity
                published_at_str = item['snippet'].get('publishedAt')
                if not published_at_str:
                    continue
                    
                published_at = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%SZ')
                
                # If this activity is older than our cutoff, we can stop
                if published_at < cutoff_date:
                    print(f"  Reached activities older than cutoff date. Stopping.")
                    return channel_last_watched
                
                # Check different activity types
                snippet = item['snippet']
                channel_id = None
                
                # For uploaded videos or recommendations
                if 'resourceId' in snippet:
                    resource_id = snippet['resourceId']
                    if resource_id.get('kind') == 'youtube#video':
                        # This is a video - get its channel
                        channel_id = snippet.get('channelId')
                
                # For playback activities (if available in contentDetails)
                content_details = item.get('contentDetails', {})
                if 'playlistItem' in content_details:
                    playlist_item = content_details['playlistItem']
                    channel_id = playlist_item.get('resourceId', {}).get('channelId')
                
                if channel_id:
                    # Update the last watched date for this channel
                    if channel_last_watched[channel_id] is None or published_at > channel_last_watched[channel_id]:
                        channel_last_watched[channel_id] = published_at
            
            print(f"  Checked {videos_checked} activities...")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
    except HttpError as e:
        print(f"An error occurred while fetching watch history: {e}")
    
    print(f"Total activities checked: {videos_checked}")
    print(f"Unique channels found in history: {len(channel_last_watched)}")
    return dict(channel_last_watched)

def get_video_watch_history(youtube, cutoff_date: datetime) -> Dict[str, datetime]:
    """
    Alternative method: Get watched videos from user's liked videos and search history.
    This is a fallback method since full watch history may not be available via API.
    
    Args:
        youtube: Authenticated YouTube API service instance.
        cutoff_date: The date to look back from (e.g., 1 year ago).
        
    Returns:
        Dictionary mapping channel IDs to their most recent view date.
    """
    print(f"\nAttempting to fetch video details from search history...")
    channel_last_watched = {}
    
    # Note: The YouTube API has limitations on accessing full watch history
    # This is a best-effort approach
    print("Note: Due to YouTube API limitations, full watch history may not be available.")
    print("The script will do its best to identify unwatched channels based on available data.")
    
    return channel_last_watched

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
    print("\nThis script will identify YouTube channels you haven't watched in over a year.")
    print("\nNote: Due to YouTube API limitations, this analysis is based on available")
    print("activity data and may not capture all viewing history.")
    print()
    
    try:
        # Authenticate with YouTube API
        youtube = get_authenticated_service()
        
        # Define cutoff date (1 year ago from today)
        cutoff_date = datetime.now() - timedelta(days=365)
        
        # Fetch all subscriptions
        subscriptions = get_all_subscriptions(youtube)
        
        if not subscriptions:
            print("No subscriptions found or unable to fetch subscriptions.")
            return
        
        # Fetch watch history
        watch_history = get_watch_history(youtube, cutoff_date)
        
        # Analyze subscriptions
        unwatched, watched = analyze_subscriptions(subscriptions, watch_history, cutoff_date)
        
        # Print results
        print_results(unwatched, watched, len(subscriptions))
        
        # Save results to file
        save_results_to_file(unwatched, watched)
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease follow the setup instructions in the README to obtain credentials.json")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

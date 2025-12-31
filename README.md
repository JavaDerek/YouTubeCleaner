# YouTubeCleaner

Get rid of unused YouTube subscriptions by identifying which channels you haven't watched in over a year.

## Overview

This Python script analyzes your YouTube channel subscriptions and viewing history to identify channels you haven't watched in the past year or more. This helps you clean up your subscription list and keep only the channels you actively watch.

## Features

- Fetches all your YouTube channel subscriptions
- Analyzes your YouTube viewing history and activity
- Identifies channels not watched in the past 365 days
- Generates detailed reports with channel information and direct links
- Saves results to a timestamped text file for future reference

## Prerequisites

- Python 3.7 or higher
- A Google account with YouTube subscriptions
- Google Cloud Project with YouTube Data API v3 enabled

## Setup Instructions

### 1. Enable YouTube Data API v3

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click on it and press "Enable"

### 2. Create OAuth 2.0 Credentials

1. In Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in the required fields (app name, user support email, developer contact)
   - Add scopes: `https://www.googleapis.com/auth/youtube.readonly` and `https://www.googleapis.com/auth/youtube.force-ssl`
   - Add your email as a test user
4. For Application type, choose "Desktop app"
5. Give it a name (e.g., "YouTubeCleaner")
6. Click "Create"
7. Download the credentials JSON file
8. Rename it to `credentials.json` and place it in the same directory as the script

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dateutil
```

## Usage

1. Make sure `credentials.json` is in the same directory as the script
2. Run the script:

```bash
python youtube_subscription_analyzer.py
```

3. On first run, your browser will open asking you to authorize the application
4. Sign in with your Google account and grant the requested permissions
5. The script will then analyze your subscriptions and viewing history
6. Results will be displayed in the console and saved to a timestamped file

## Output

The script generates two outputs:

1. **Console Output**: Displays a summary of your subscriptions, listing channels not watched in over a year
2. **Text File**: A detailed report saved as `youtube_subscription_analysis_YYYYMMDD_HHMMSS.txt`

### Example Output

See [example_output.txt](example_output.txt) for a sample of what the generated report looks like.

```
================================================================================
YOUTUBE SUBSCRIPTION ANALYSIS RESULTS
================================================================================

Total Subscriptions: 150
Watched in last year: 120
NOT watched in last year: 30

--------------------------------------------------------------------------------
CHANNELS NOT WATCHED IN OVER ONE YEAR:
--------------------------------------------------------------------------------

1. Example Channel Name
   Channel ID: UCxxxxxxxxxxxxxxxxxx
   Status: Last watched 2023-01-15
   URL: https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxx
...
```

## Important Notes

### YouTube API Limitations

- The YouTube Data API has limitations on accessing complete watch history
- The script uses the Activities API which provides available activity data
- Some viewing history may not be captured due to API restrictions
- Results represent a best-effort analysis based on available data

### Privacy & Security

- Your `credentials.json` and `token.pickle` files contain sensitive authentication data
- These files are excluded from version control via `.gitignore`
- Never share these files publicly
- The script only reads data; it does not modify your subscriptions

### API Quotas

- YouTube Data API v3 has daily quota limits (10,000 units per day for free tier)
- This script typically uses 200-500 quota units per run depending on subscription count
- If you hit quota limits, wait 24 hours or request a quota increase

## Troubleshooting

### "credentials.json file not found"
- Make sure you've downloaded the OAuth credentials and renamed them to `credentials.json`
- Place the file in the same directory as the script

### "Access Not Configured"
- Ensure YouTube Data API v3 is enabled in your Google Cloud project

### "The user has not granted the app permission"
- Make sure you've added your email as a test user in the OAuth consent screen
- Grant all requested permissions when authorizing the app

### Limited History Data
- The YouTube API may not provide complete watch history
- The script analyzes available activity data to make the best assessment

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

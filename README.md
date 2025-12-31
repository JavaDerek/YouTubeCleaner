# YouTubeCleaner

Get rid of unused YouTube subscriptions by identifying which channels you haven't watched in over a year.

## Overview

**YouTubeCleaner** helps you clean up your YouTube subscriptions by identifying channels you are subscribed to but haven’t actually watched recently.

Due to changes in Google’s APIs, **YouTube watch history is no longer accessible via the YouTube Data API**. As a result, this tool combines:

* **YouTube Data API v3** (to fetch current subscriptions), and
* **Google Takeout watch-history export** (to analyze actual viewing behavior)

This is now the *only supported and reliable* way to perform this analysis.

---

## Features

* Fetches all current YouTube channel subscriptions via API
* Analyzes **actual watch history** using Google Takeout JSON
* Identifies channels not watched in the past 365 days
* **Interactive unsubscribe feature** - choose which channels to unsubscribe from
* Generates detailed reports with channel names, IDs, and direct links
* Saves results to a timestamped text file for future reference

---

## Prerequisites

* Python 3.7 or higher
* A Google account with YouTube subscriptions
* A Google Cloud project with **YouTube Data API v3 enabled**
* A Google Takeout export containing YouTube watch history

---

## Setup Instructions

### 1. Enable YouTube Data API v3

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:

   * Navigate to **APIs & Services → Library**
   * Search for **YouTube Data API v3**
   * Click **Enable**

---

### 2. Configure OAuth (Google Auth Platform – current UI)

Google’s UI has changed. OAuth configuration is now split across multiple sections.

#### 2.1 Configure OAuth Consent Screen

1. In Google Cloud Console, go to **Google Auth Platform**
2. Open **Branding**

   * Set an app name
   * Set user support email and developer contact email
3. Open **Audience**

   * Choose **External**
   * Add **your own email address** as a **Test user**

#### 2.2 Add OAuth Scopes

1. Go to **Data Access**
2. Click **Add or Remove Scopes**
3. Add the following scopes:

   ```
   https://www.googleapis.com/auth/youtube
   https://www.googleapis.com/auth/youtube.force-ssl
   ```

   > Note: `youtube` scope (not `youtube.readonly`) is required for the unsubscribe feature.
   > These scopes are classified by Google as **Sensitive**, not Restricted.
   > No app verification is required as long as you remain in Testing.

Save changes.

---

### 2.3 Create OAuth Client (Desktop App)

1. Go to **Clients**
2. Click **Create OAuth client**
3. Set:

   * **Application type:** Desktop app
   * **Name:** YouTubeCleaner
4. Click **Create**
5. Download the JSON file
6. Rename it to `credentials.json`
7. Place it in the same directory as the script

---

### 3. Export Watch History via Google Takeout (Required)

Because YouTube no longer exposes watch history via API, you must use Google Takeout.

1. Go to [https://takeout.google.com](https://takeout.google.com)
2. Click **Deselect all**
3. Select **YouTube and YouTube Music**
4. Click **All YouTube data included**
5. Deselect everything except:

   * **history → watch-history**
6. Continue and create a one-time export
7. Download and unzip the archive

You should end up with a file at:

```
Takeout/
└── YouTube and YouTube Music/
    └── history/
        └── watch-history.json
```

Place `watch-history.json` where the script expects it (see script documentation or config).

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

Or individually:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dateutil
```

---

## Usage

1. Ensure the following files are present:

   * `credentials.json`
   * `watch-history.json`
2. Run the script:

```bash
python youtube_subscription_analyzer.py
```

3. On first run:

   * A browser window will open
   * Sign in with your Google account
   * Grant the requested permissions

4. The script will:

   * Fetch subscriptions via the YouTube Data API
   * Analyze watch his
   * Prompt you to optionally unsubscribe from unwatched channelstory from the Takeout export
   * Generate a report

---

## Output

The script generates two outputs:

1. **Console Output**
   Summary of subscriptions and inactive channels

2. **Text File**
   Detailed report saved as:

   ```
   youtube_subscription_analysis_YYYYMMDD_HHMMSS.txt
   ```

### Example Output

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
```

---

## Important Notes

### YouTube API Limitations (Updated)

* ❌ YouTube **no longer provides watch history via API**
* ❌ The Activities API does **not** expose reliable viewing data
* ✅ Google Takeout is now the **only supported source** for personal watch history

This tool reflects that reality.

---

### Privacy & Security

* `credentials.json`, OAuth tokens, and Takeout exports contain **sensitive personal data**
* These filescan unsubscribe from channels (requires your explicit confirmation)
* Never commit or share them publicly
* The script is **read-only** and does not modify subscriptions

---

### API Quotas

* YouTube Data API v3 free tier: **10,000 units/day**
* Typical usage per run: **200–500 units**
* Watch history analysis does **not** consume API quota

---

## Troubleshooting

### OAuth client creation button missing

* Ensure **Branding** and **Audience** are fully configured
* Google hides OAuth client creation until those steps are complete

### `credentials.json` file not found

* Ensure the downloaded OAuth client file is renamed correctly
* Place it next to the script

### `Access Not Configured`

* Confirm YouTube Data API v3 is enabled in the correct project

### Missing or incomplete history

* Google Takeout reflects only what Google has retained
* Paused or deleted history will not appear

---

## License

See `LICENSE` file for details.

---

## Contributing

Contributions are welcome.

If Google changes APIs (again), please open an issue so the tool can be updated accordingly.

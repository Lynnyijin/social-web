# The Social Web

Course work for VU Amsterdam X_405086 The Social Web (2025)

## Steam Review Scraper

A Python script to scrape English reviews from Steam community pages using Selenium.

## Features

- Scrapes reviews from Steam game pages
- Filters for English reviews only
- Extracts comprehensive review data including:
  - User information (Steam ID, username, profile URL)
  - Review content and metadata
  - Play hours
  - Recommendation status
  - Review dates
  - And more...

## Requirements

- Python 3.7+
- Microsoft Edge / Chrome browser installed
- Edge / Chrome WebDriver (automatically managed by Selenium 4.6+)

## Installation

1. Install required Python packages:

```bash
pip install selenium
```

2. Make sure Microsoft Edge browser is installed on your system.

## Configuration

Edit the configuration variables at the top of `data_scrape.py`:

```python
GAME_ID = 1172470  # Change to your target game ID
REVIEW_TYPE = 'negativereviews'  # Options: 'negativereviews' or 'positivereviews'
LANGUAGE_FILTER = 'english'
```

## Usage

Run the script:

```bash
python data_scrape.py
```

The script will:

1. Open Edge browser and navigate to the Steam review page
2. Automatically scroll to load more reviews
3. Collect English reviews only
4. Save data to a CSV file: `Steam_Reviews_{GAME_ID}_{DATE}.csv`

## Output

The CSV file contains the following columns:

- ReviewId
- SteamId
- UserName
- ProfileURL
- ReviewText
- ReviewLength_Chars
- ReviewLength_Words
- IsRecommended
- PlayHours_Text
- PlayHours_Numeric
- ReviewLanguage
- DatePosted
- ReviewURL

## Notes

- The script only collects English reviews
- Duplicate reviews are automatically skipped
- The browser window will open during scraping (you can minimize it)
- Progress messages are displayed in the console

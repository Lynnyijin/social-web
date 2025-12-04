"""
Steam Review Scraper
Scrapes English reviews from Steam community pages
"""

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import re
from time import sleep
from datetime import datetime
import csv
import argparse
import json
from typing import List, Dict, Any
import requests


# Configuration
LANGUAGE_FILTER = 'english'
MAX_SCROLL_ATTEMPTS = 3
SCROLL_WAIT_TIME = 1.0
PAGE_LOAD_WAIT = 2.0
MAX_SCROLLS_PER_GAME = 200
DEFAULT_TARGET_POSITIVE = 500
DEFAULT_TARGET_NEGATIVE = 500
DEFAULT_OUTPUT_FILE = 'steam_reviews_all_games.csv'
STORE_URL_TEMPLATE = 'https://store.steampowered.com/app/{game_id}/'


# Default game configuration (can be overridden via CLI config file)
DEFAULT_GAME_CONFIG: List[Dict[str, Any]] = [
    # FPS
    {"game_id": 1172470, "game_name": "Apex Legends", "genre": "FPS", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 730, "game_name": "Counter-Strike 2", "genre": "FPS", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 2807960, "game_name": "Battlefield 6", "genre": "FPS", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 3606480, "game_name": "Call of Duty: Black Ops 7", "genre": "FPS", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    # RPG
    {"game_id": 1245620, "game_name": "ELDEN RING", "genre": "RPG", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 990080, "game_name": "Hogwarts Legacy", "genre": "RPG", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 2161700, "game_name": "Persona 3 Reload", "genre": "RPG", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    # Indie
    {"game_id": 1426210, "game_name": "It Takes Two", "genre": "Indie", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 1030300, "game_name": "Hollow Knight: Silksong", "genre": "Indie", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 413150, "game_name": "Stardew Valley", "genre": "Indie", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    # Strategy
    {"game_id": 1466860, "game_name": "Age of Empires IV", "genre": "Strategy", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 289070, "game_name": "Sid Meier's Civilization VI", "genre": "Strategy", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 394360, "game_name": "Hearts of Iron IV", "genre": "Strategy", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    # Simulation
    {"game_id": 1222670, "game_name": "The Sims 4", "genre": "Simulation", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 2300320, "game_name": "Farming Simulator 25", "genre": "Simulation", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 270880, "game_name": "American Truck Simulator", "genre": "Simulation", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    # MOBA
    {"game_id": 570, "game_name": "Dota 2", "genre": "MOBA", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 2357570, "game_name": "Overwatch 2", "genre": "MOBA", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 1283700, "game_name": "SUPERVIVE", "genre": "MOBA", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    # Co-op / Multiplayer
    {"game_id": 3527290, "game_name": "PEAK", "genre": "Co-op / Multiplayer", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 550, "game_name": "Left 4 Dead 2", "genre": "Co-op / Multiplayer", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 648800, "game_name": "Raft", "genre": "Co-op / Multiplayer", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 2246340, "game_name": "Monster Hunter Wilds", "genre": "Co-op / Multiplayer", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
    {"game_id": 2001120, "game_name": "Split Fiction", "genre": "Co-op / Multiplayer", "target_positive": DEFAULT_TARGET_POSITIVE, "target_negative": DEFAULT_TARGET_NEGATIVE},
]


def create_driver():
    """Create and configure Edge WebDriver"""
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    return webdriver.Edge(options=options)


def bypass_content_warning(driver):
    """
    Some games show a content warning / age gate on the community page.
    Try to click the \"View Community Hub\" button so we can see reviews.
    """
    try:
        # Prefer the known button class if present (works for <button> and <a>)
        try:
            button = driver.find_element(
                By.CSS_SELECTOR, "button.btn_blue_steamui.btn_medium, a.btn_blue_steamui.btn_medium"
            )
        except NoSuchElementException:
            # Fallback: look for the primary button with this label
            button = driver.find_element(
                By.XPATH,
                "//*[contains(@class, 'btn_blue_steamui') and contains(., 'View Community Hub')]",
            )

        if button:
            button.click()
            sleep(PAGE_LOAD_WAIT)
            print("Bypassed content warning by clicking 'View Community Hub'.")
    except NoSuchElementException:
        # No gate on this page – nothing to do
        return
    except Exception as exc:
        print(f"Warning: Failed to bypass content warning: {exc}")


def get_review_url(game_id, review_type, language):
    """Generate Steam review URL with language filter"""
    base_url = f'https://steamcommunity.com/app/{game_id}/{review_type}/'
    params = '?browsefilter=mostrecent&filterLanguage=' + language
    return base_url + params


def fetch_game_metadata(game_id):
    """Fetch overall review summary, review count, and tags from Steam store page"""
    url = STORE_URL_TEMPLATE.format(game_id=game_id)
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    }
    metadata = {
        'overall_review_summary': '',
        'total_review_count': '',
        'store_tags': [],
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        summary_match = re.search(
            r'class="game_review_summary.*?>(.*?)<', html, re.IGNORECASE | re.DOTALL
        )
        if summary_match:
            metadata['overall_review_summary'] = summary_match.group(1).strip()

        count_match = re.search(
            r'responsive_reviewdesc">.*?\(([\d,]+)\)', html, re.IGNORECASE | re.DOTALL
        )
        if count_match:
            metadata['total_review_count'] = count_match.group(1).strip()

        tag_matches = re.findall(r'class="app_tag".*?>(.*?)<', html, re.IGNORECASE | re.DOTALL)
        tags = [tag.strip() for tag in tag_matches if tag.strip()]
        metadata['store_tags'] = tags[:10]  # limit to top 10 tags

    except Exception as exc:
        print(f"Warning: Could not fetch metadata for game {game_id}: {exc}")

    return metadata


def extract_helpful_votes(card):
    """Extract helpful vote count from a review card"""
    text = safe_find_element(card, './/div[contains(@class, "found_helpful")]', "")
    if not text:
        return 0
    match = re.search(r'(\d+)', text.replace(',', ''))
    return int(match.group(1)) if match else 0


def safe_find_element(card, xpath, default=""):
    """Safely find element by XPath, return default if not found"""
    try:
        element = card.find_element(By.XPATH, xpath)
        return element.text if hasattr(element, 'text') else element.get_attribute('href') or element.get_attribute('src') or default
    except (NoSuchElementException, StaleElementReferenceException):
        return default


def extract_numeric_value(text, pattern=r'(\d+\.?\d*)'):
    """Extract numeric value from text using regex"""
    match = re.search(pattern, text)
    return float(match.group(1)) if match else 0.0


def is_english_review(card):
    """Check if review is in English"""
    # Check language indicator if available
    language = safe_find_element(card, './/div[contains(@class, "language")]', "")
    if language:
        return 'english' in language.lower()
    
    # If no language indicator, assume English (since URL filters for English)
    # Additional check: look for common non-English characters
    review_content = safe_find_element(card, './/div[@class="apphub_CardTextContent"]', "")
    if review_content:
        # Check for common non-English character patterns
        non_english_patterns = [
            r'[\u4e00-\u9fff]',  # Chinese
            r'[\u3040-\u309f\u30a0-\u30ff]',  # Japanese
            r'[\u0400-\u04ff]',  # Cyrillic
            r'[\u0590-\u05ff]',  # Hebrew
            r'[\u0600-\u06ff]',  # Arabic
        ]
        for pattern in non_english_patterns:
            if re.search(pattern, review_content):
                return False
    
    return True


def extract_review_data(card):
    """Extract all data from a review card"""
    try:
        # Get profile link element (used for both URL and username)
        profile_link = card.find_element(By.XPATH, './/div[@class="apphub_friend_block"]/div/a[2]')
        profile_url = profile_link.get_attribute('href')
        steam_id = profile_url.split('/')[-2]
        user_name = profile_link.text or "Unknown"
        
        # Extract date and review content
        date_posted = safe_find_element(card, './/div[@class="apphub_CardTextContent"]/div', "")
        review_content_elem = card.find_element(By.XPATH, './/div[@class="apphub_CardTextContent"]')
        review_content = review_content_elem.text.replace(date_posted, '').strip()
        
        # Calculate review lengths
        review_length_chars = len(review_content.replace(' ', ''))
        review_length_words = len(review_content.split())
        
        # Extract recommendation status
        thumb_text = safe_find_element(card, './/div[@class="reviewInfo"]/div[2]', "")
        if thumb_text:
            # Check for "Not Recommended" first, then "Recommended"
            if "Not Recommended" in thumb_text:
                is_recommended = False
            elif "Recommended" in thumb_text:
                is_recommended = True
            else:
                is_recommended = None
        else:
            is_recommended = None
        
        # Extract play hours
        play_hours_text = safe_find_element(card, './/div[@class="reviewInfo"]/div[3]', "")
        play_hours = extract_numeric_value(play_hours_text)
        
        # Extract review language
        review_language = safe_find_element(card, './/div[contains(@class, "language")]', "")
        
        # Extract review ID and URL
        review_id = ""
        review_url = ""
        try:
            review_link = card.find_element(By.XPATH, './/a[contains(@href, "recommended")]')
            review_url = review_link.get_attribute('href')
            review_id_match = re.search(r'recommended/(\d+)', review_url)
            review_id = review_id_match.group(1) if review_id_match else ""
        except NoSuchElementException:
            pass

        helpful_votes = extract_helpful_votes(card)

        return {
            'review_id': review_id,
            'steam_id': steam_id,
            'user_name': user_name,
            'profile_url': profile_url,
            'review_content': review_content,
            'review_length_chars': review_length_chars,
            'review_length_words': review_length_words,
            'is_recommended': is_recommended,
            'play_hours_text': play_hours_text,
            'play_hours': play_hours,
            'review_language': review_language,
            'date_posted': date_posted,
            'review_url': review_url,
            'helpful_votes': helpful_votes,
        }
    except (NoSuchElementException, StaleElementReferenceException) as e:
        print(f"Error extracting review data: {e}")
        return None


def scroll_to_load_more(driver, last_position, max_attempts=MAX_SCROLL_ATTEMPTS):
    """Scroll page to load more reviews"""
    scroll_attempt = 0
    
    while scroll_attempt < max_attempts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(SCROLL_WAIT_TIME)
        driver.execute_script("window.scrollBy(0, 500);")
        sleep(SCROLL_WAIT_TIME / 2)
        
        curr_position = driver.execute_script("return window.pageYOffset;")
        
        if curr_position == last_position:
            scroll_attempt += 1
            sleep(SCROLL_WAIT_TIME)
            if scroll_attempt >= max_attempts:
                return None, True  # Reached end
        else:
            return curr_position, False  # Made progress
    
    return None, True


def scrape_reviews_for_game(driver, game, review_type, target_count, language=LANGUAGE_FILTER, game_metadata=None):
    """
    Scrape reviews for a single game and sentiment until target_count or page end.
    review_type: 'positivereviews' or 'negativereviews'
    """
    game_id = game['game_id']
    game_name = game.get('game_name', str(game_id))
    genre = game.get('genre', '')
    sentiment = 'positive' if review_type == 'positivereviews' else 'negative'

    url = get_review_url(game_id, review_type, language)
    print(f"\nScraping {sentiment} reviews for {game_name} (ID {game_id}) from: {url}")

    driver.get(url)
    sleep(PAGE_LOAD_WAIT)
    # Some games show a content warning / age gate – try to skip it
    bypass_content_warning(driver)
    driver.maximize_window()
    sleep(1)

    reviews = []
    review_ids = set()
    last_position = driver.execute_script("return window.pageYOffset;")
    running = True
    scrolls = 0

    while running and len(reviews) < target_count and scrolls < MAX_SCROLLS_PER_GAME:
        # Get all review cards on current page
        try:
            cards = driver.find_elements(By.CLASS_NAME, 'apphub_Card')
            print(f"Found {len(cards)} review cards on page")
        except Exception as e:
            print(f"Error finding cards: {e}")
            break

        # Process each card
        for card in cards:
            if len(reviews) >= target_count:
                break
            try:
                # Extract review data
                review_data = extract_review_data(card)
                if not review_data:
                    continue

                # Skip if already collected (by review_id if possible, else steam_id)
                unique_key = review_data['review_id'] or review_data['steam_id']
                if unique_key in review_ids:
                    continue

                # Only collect English reviews
                if not is_english_review(card):
                    print(f"Skipping non-English review from {review_data['user_name']}")
                    continue

                # Add game-level and sentiment info
                metadata_fields = game_metadata or {}
                review_data.update(
                    {
                        'game_id': game_id,
                        'game_name': game_name,
                        'genre': genre,
                        'sentiment': sentiment,
                        'overall_review_summary': metadata_fields.get('overall_review_summary', ''),
                        'total_review_count': metadata_fields.get('total_review_count', ''),
                        'store_tags': metadata_fields.get('store_tags', []),
                    }
                )

                # Add to collection
                review_ids.add(unique_key)
                reviews.append(review_data)
                print(
                    f"Collected {len(reviews)}/{target_count} {sentiment} reviews for "
                    f"{game_name}: {review_data['user_name']} - {review_data['play_hours']} hours"
                )

            except StaleElementReferenceException:
                print("Stale element, skipping card")
                continue
            except Exception as e:
                print(f"Error processing card: {e}")
                continue

        # Scroll to load more reviews
        last_position, reached_end = scroll_to_load_more(driver, last_position)
        scrolls += 1
        if reached_end:
            print(
                f"Reached end of page for {game_name} ({sentiment}). "
                f"Total reviews collected: {len(reviews)}"
            )
            running = False
        else:
            print(
                f"Scrolled to position {last_position}, "
                f"found {len(reviews)} {sentiment} reviews so far for {game_name}"
            )

    if len(reviews) < target_count:
        print(
            f"Warning: Only collected {len(reviews)}/{target_count} {sentiment} reviews for {game_name}"
        )
    if scrolls >= MAX_SCROLLS_PER_GAME:
        print(
            f"Reached max scroll limit ({MAX_SCROLLS_PER_GAME}) for {game_name} "
            f"while collecting {sentiment} reviews"
        )

    return reviews


def run_batch_scrape(
    driver,
    game_list,
    language=LANGUAGE_FILTER,
    writer=None,
    start_index=1,
):
    """
    Run scraping for all games and sentiments.

    If writer is provided, rows are written to CSV in real time and we keep a
    running GlobalReviewId starting from start_index.
    """
    all_reviews = []
    global_id = start_index

    for game in game_list:
        positive_target = game.get('target_positive', DEFAULT_TARGET_POSITIVE)
        negative_target = game.get('target_negative', DEFAULT_TARGET_NEGATIVE)
        print(
            f"\n=== Starting game {game.get('game_name', game['game_id'])} "
            f"(positive target: {positive_target}, negative target: {negative_target}) ==="
        )

        metadata = fetch_game_metadata(game['game_id'])

        # Positive reviews
        if positive_target > 0:
            try:
                positive_reviews = scrape_reviews_for_game(
                    driver,
                    game,
                    review_type='positivereviews',
                    target_count=positive_target,
                    language=language,
                    game_metadata=metadata,
                )
                all_reviews.extend(positive_reviews)
            except Exception as exc:
                print(
                    f"Error scraping positive reviews for {game.get('game_name')}: {exc}"
                )

        # Negative reviews
        if negative_target > 0:
            try:
                negative_reviews = scrape_reviews_for_game(
                    driver,
                    game,
                    review_type='negativereviews',
                    target_count=negative_target,
                    language=language,
                    game_metadata=metadata,
                )
                all_reviews.extend(negative_reviews)
            except Exception as exc:
                print(
                    f"Error scraping negative reviews for {game.get('game_name')}: {exc}"
                )

        print(
            f"Finished {game.get('game_name', game['game_id'])}: "
            f"{positive_target} positive, {negative_target} negative targets."
        )

        # If streaming to CSV, write as we go
        if writer is not None:
            for review in all_reviews:
                writer.writerow({
                    'GlobalReviewId': global_id,
                    'GameId': review.get('game_id'),
                    'GameName': review.get('game_name'),
                    'Genre': review.get('genre'),
                    'Sentiment': review.get('sentiment'),
                    'ReviewId': review.get('review_id'),
                    'SteamId': review['steam_id'],
                    'UserName': review['user_name'],
                    'ProfileURL': review['profile_url'],
                    'ReviewText': review['review_content'],
                    'ReviewLength_Chars': review['review_length_chars'],
                    'ReviewLength_Words': review['review_length_words'],
                    'IsRecommended': review['is_recommended'],
                    'HelpfulVotes': review.get('helpful_votes'),
                    'PlayHours_Text': review['play_hours_text'],
                    'PlayHours_Numeric': review['play_hours'],
                    'ReviewLanguage': review['review_language'],
                    'DatePosted': review['date_posted'],
                    'ReviewURL': review['review_url'],
                    'OverallReviewSummary': review.get('overall_review_summary'),
                    'TotalReviewCount': review.get('total_review_count'),
                    'StoreTags': '|'.join(review.get('store_tags', [])) if review.get('store_tags') else '',
                })
                global_id += 1
            # Clear memory – reviews are already on disk
            all_reviews.clear()

    return all_reviews, global_id


def load_game_list(config_path, default_positive, default_negative):
    """
    Load game configuration list from JSON file or fallback to defaults.
    Ensures target counts have sensible defaults.
    """
    if config_path:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = json.load(f)
            print(f"Loaded game configuration from {config_path}")
        except Exception as exc:
            raise RuntimeError(f"Failed to load config file {config_path}: {exc}") from exc
    else:
        raw_config = DEFAULT_GAME_CONFIG
        print("Using built-in default game configuration")

    normalized_config = []
    for game in raw_config:
        entry = {
            'game_id': int(game['game_id']),
            'game_name': game.get('game_name', str(game['game_id'])),
            'genre': game.get('genre', 'Unknown'),
            'target_positive': game.get('target_positive', default_positive),
            'target_negative': game.get('target_negative', default_negative),
        }
        normalized_config.append(entry)

    return normalized_config


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Batch Steam review scraper")
    parser.add_argument('--config', help='Path to JSON file containing game list', default=None)
    parser.add_argument('--language', default=LANGUAGE_FILTER, help='Language filter for reviews')
    parser.add_argument('--output', default=DEFAULT_OUTPUT_FILE, help='Output CSV filename')
    parser.add_argument('--default-positive', type=int, default=DEFAULT_TARGET_POSITIVE,
                        help='Default positive review target per game')
    parser.add_argument('--default-negative', type=int, default=DEFAULT_TARGET_NEGATIVE,
                        help='Default negative review target per game')
    parser.add_argument('--max-scrolls-per-game', type=int, default=MAX_SCROLLS_PER_GAME,
                        help='Safety cap on scroll iterations per game')
    parser.add_argument('--max-scroll-attempts', type=int, default=MAX_SCROLL_ATTEMPTS,
                        help='Attempts before assuming page end when scroll position is static')
    parser.add_argument('--scroll-wait', type=float, default=SCROLL_WAIT_TIME,
                        help='Wait (seconds) between scroll actions')
    parser.add_argument('--page-wait', type=float, default=PAGE_LOAD_WAIT,
                        help='Wait (seconds) after loading each page')
    return parser.parse_args()


def apply_runtime_overrides(args):
    """Apply runtime configuration overrides from CLI arguments"""
    global MAX_SCROLLS_PER_GAME, MAX_SCROLL_ATTEMPTS, SCROLL_WAIT_TIME, PAGE_LOAD_WAIT
    MAX_SCROLLS_PER_GAME = args.max_scrolls_per_game
    MAX_SCROLL_ATTEMPTS = args.max_scroll_attempts
    SCROLL_WAIT_TIME = args.scroll_wait
    PAGE_LOAD_WAIT = args.page_wait


def save_to_csv(reviews, filename=DEFAULT_OUTPUT_FILE):
    """Save reviews to CSV file"""
    if not reviews:
        print("No reviews to save!")
        return
    
    # today = datetime.today().strftime('%Y%m%d')
    # filename = f'Steam_Reviews_{game_id}_{today}.csv'
    # filename = f'Steam_Reviews_{game_id}.csv'
    
    fieldnames = [
        'GlobalReviewId',
        'GameId',
        'GameName',
        'Genre',
        'Sentiment',
        'ReviewId',
        'SteamId',
        'UserName',
        'ProfileURL',
        'ReviewText',
        'ReviewLength_Chars',
        'ReviewLength_Words',
        'IsRecommended',
        'HelpfulVotes',
        'PlayHours_Text',
        'PlayHours_Numeric',
        'ReviewLanguage',
        'DatePosted',
        'ReviewURL',
        'OverallReviewSummary',
        'TotalReviewCount',
        'StoreTags',
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=';',
        )
        writer.writeheader()

        # Add sequential reviewID starting from 1
        for idx, review in enumerate(reviews, start=1):
            writer.writerow({
                'GlobalReviewId': idx,
                'GameId': review.get('game_id'),
                'GameName': review.get('game_name'),
                'Genre': review.get('genre'),
                'Sentiment': review.get('sentiment'),
                'ReviewId': review.get('review_id'),
                'SteamId': review['steam_id'],
                'UserName': review['user_name'],
                'ProfileURL': review['profile_url'],
                'ReviewText': review['review_content'],
                'ReviewLength_Chars': review['review_length_chars'],
                'ReviewLength_Words': review['review_length_words'],
                'IsRecommended': review['is_recommended'],
                'HelpfulVotes': review.get('helpful_votes'),
                'PlayHours_Text': review['play_hours_text'],
                'PlayHours_Numeric': review['play_hours'],
                'ReviewLanguage': review['review_language'],
                'DatePosted': review['date_posted'],
                'ReviewURL': review['review_url'],
                'OverallReviewSummary': review.get('overall_review_summary'),
                'TotalReviewCount': review.get('total_review_count'),
                'StoreTags': '|'.join(review.get('store_tags', [])) if review.get('store_tags') else '',
            })
    
    print(f"\nTotal reviews collected: {len(reviews)}")
    print(f"Data saved to {filename}")


def main():
    """Main execution function"""
    args = parse_args()
    apply_runtime_overrides(args)

    game_list = load_game_list(
        args.config,
        default_positive=args.default_positive,
        default_negative=args.default_negative,
    )

    # Open CSV once and stream rows as we scrape so progress is never lost
    fieldnames = [
        'GlobalReviewId',
        'GameId',
        'GameName',
        'Genre',
        'Sentiment',
        'ReviewId',
        'SteamId',
        'UserName',
        'ProfileURL',
        'ReviewText',
        'ReviewLength_Chars',
        'ReviewLength_Words',
        'IsRecommended',
        'HelpfulVotes',
        'PlayHours_Text',
        'PlayHours_Numeric',
        'ReviewLanguage',
        'DatePosted',
        'ReviewURL',
        'OverallReviewSummary',
        'TotalReviewCount',
        'StoreTags',
    ]

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        driver = create_driver()
        try:
            # We ignore the returned list to keep memory low; data is on disk
            _, final_id = run_batch_scrape(
                driver,
                game_list,
                language=args.language,
                writer=writer,
                start_index=1,
            )
            print(f"\nStreaming write complete. Last GlobalReviewId: {final_id - 1}")
        finally:
            driver.quit()
            print("WebDriver closed.")


if __name__ == "__main__":
    main()

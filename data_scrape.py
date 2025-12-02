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


# Configuration
GAME_ID = 1172470
REVIEW_TYPE = 'negativereviews'  # Options: 'negativereviews' or 'positivereviews'
LANGUAGE_FILTER = 'english'
MAX_SCROLL_ATTEMPTS = 1
SCROLL_WAIT_TIME = 1.0
PAGE_LOAD_WAIT = 2.0


def create_driver():
    """Create and configure Edge WebDriver"""
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    return webdriver.Edge(options=options)


def get_review_url(game_id, review_type, language):
    """Generate Steam review URL with language filter"""
    base_url = f'https://steamcommunity.com/app/{game_id}/{review_type}/'
    params = '?browsefilter=mostrecent&filterLanguage=' + language
    return base_url + params


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
            'review_url': review_url
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


def scrape_reviews(driver, url):
    """Main scraping function"""
    driver.get(url)
    sleep(PAGE_LOAD_WAIT)
    driver.maximize_window()
    sleep(1)
    
    reviews = []
    review_ids = set()
    last_position = driver.execute_script("return window.pageYOffset;")
    running = True
    
    while running:
        # Get all review cards on current page
        try:
            cards = driver.find_elements(By.CLASS_NAME, 'apphub_Card')
            print(f"Found {len(cards)} review cards on page")
        except Exception as e:
            print(f"Error finding cards: {e}")
            break
        
        # Process each card
        for card in cards:
            try:
                # Extract review data
                review_data = extract_review_data(card)
                if not review_data:
                    continue
                
                # Skip if already collected
                if review_data['steam_id'] in review_ids:
                    continue
                
                # Only collect English reviews
                if not is_english_review(card):
                    print(f"Skipping non-English review from {review_data['user_name']}")
                    continue
                
                # Add to collection
                review_ids.add(review_data['steam_id'])
                reviews.append(review_data)
                print(f"Collected review {len(reviews)}: {review_data['user_name']} - {review_data['play_hours']} hours")
                
            except StaleElementReferenceException:
                print("Stale element, skipping card")
                continue
            except Exception as e:
                print(f"Error processing card: {e}")
                continue
        
        # Scroll to load more reviews
        last_position, reached_end = scroll_to_load_more(driver, last_position)
        if reached_end:
            print(f"Reached end of page. Total reviews collected: {len(reviews)}")
            running = False
        else:
            print(f"Scrolled to position {last_position}, found {len(reviews)} reviews so far")
    
    return reviews


def save_to_csv(reviews, game_id):
    """Save reviews to CSV file"""
    if not reviews:
        print("No reviews to save!")
        return
    
    # today = datetime.today().strftime('%Y%m%d')
    # filename = f'Steam_Reviews_{game_id}_{today}.csv'
    filename = f'Steam_Reviews_{game_id}.csv'
    
    fieldnames = [
        'ReviewId',
        'SteamId',
        'UserName',
        'ProfileURL',
        'ReviewText',
        'ReviewLength_Chars',
        'ReviewLength_Words',
        'IsRecommended',
        'PlayHours_Text',
        'PlayHours_Numeric',
        'ReviewLanguage',
        'DatePosted',
        'ReviewURL'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Add sequential reviewID starting from 1
        for idx, review in enumerate(reviews, start=1):
            writer.writerow({
                'ReviewId': idx,  # Sequential ID starting from 1
                'SteamId': review['steam_id'],
                'UserName': review['user_name'],
                'ProfileURL': review['profile_url'],
                'ReviewText': review['review_content'],
                'ReviewLength_Chars': review['review_length_chars'],
                'ReviewLength_Words': review['review_length_words'],
                'IsRecommended': review['is_recommended'],
                'PlayHours_Text': review['play_hours_text'],
                'PlayHours_Numeric': review['play_hours'],
                'ReviewLanguage': review['review_language'],
                'DatePosted': review['date_posted'],
                'ReviewURL': review['review_url']
            })
    
    print(f"\nTotal reviews collected: {len(reviews)}")
    print(f"Data saved to {filename}")


def main():
    """Main execution function"""
    url = get_review_url(GAME_ID, REVIEW_TYPE, LANGUAGE_FILTER)
    print(f"Scraping reviews from: {url}")
    
    driver = create_driver()
    try:
        reviews = scrape_reviews(driver, url)
        save_to_csv(reviews, GAME_ID)
    finally:
        driver.close()
        print("WebDriver closed.")


if __name__ == "__main__":
    main()

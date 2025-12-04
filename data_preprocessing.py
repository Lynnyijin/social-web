import pandas as pd
import re
import requests

from langdetect import detect
from datetime import datetime


game_appids = [1172470]
game_metadata = {}


class ReviewFilteringHelper:
    @classmethod
    def is_english(cls, text):
        """Detect English reviews using langdetect."""
        try:
            return detect(text) == "en"
        except:
            return False

    @classmethod
    def parse_hours(cls, text):
        if pd.isna(text):
            return 0.0
        # Example: "148.5 hrs on record"
        value = re.findall(r"[\d\.]+", str(text))
        if value:
            return float(value[0])
        return 0.0
    
    @classmethod
    def clean_date(cls, text):
        if pd.isna(text):
            return None

        # Example: 'Posted: 3 December'
        text = text.replace("Posted: ", "").strip()

        # Try parsing "3 December"
        try:
            parsed_date = datetime.strptime(text, '%B %d')
        except ValueError:
            try:
                parsed_date = datetime.strptime(text, '%d %B')
            except ValueError:
                return None
        parsed_date = parsed_date.replace(year=datetime.now().year)
        return parsed_date.strftime("%Y-%m-%d")
    
    @classmethod
    def preprocess(cls):
        filename = f"steam_reviews_all_games.csv"
        df = pd.read_csv(filename, sep=";")
        df["GlobalReviewId"] = pd.to_numeric(df["GlobalReviewId"], errors="coerce").fillna(0).astype(int)
        df["TotalReviewCount"] = (
            df["TotalReviewCount"]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df["TotalReviewCount"] = pd.to_numeric(df["TotalReviewCount"], errors="coerce").fillna(0).astype(int)
        df = df[df["ReviewText"].fillna("").str.len() > 5]
        df = df[df["ReviewText"].apply(cls.is_english)]
        df = df.drop_duplicates(subset=["ReviewText"])
        df["PlayHours"] = df["PlayHours_Text"].apply(cls.parse_hours)
        df["DatePosted"] = df["DatePosted"].apply(cls.clean_date)

        columns_to_drop = [
            "SteamId", "UserName", "ProfileURL", "ReviewURL",
            "GameName", "ReviewId",
            "ReviewLength_Chars", "ReviewLength_Words",
            "PlayHours_Text", "ReviewLanguage",
            "OverallReviewSummary", "StoreTags"
        ]
        df = df.drop(columns=[c for c in columns_to_drop if c in df.columns])
        return df


class GameMetadataHelper:
    @classmethod
    def parse_steam_metadata(cls, appid):
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        res = requests.get(url).json()
        
        data = res[str(appid)]["data"]
        name = data.get("name", "Unknown")
        recommendations = data.get("recommendations", {}).get("total", 0)
        release_raw = data.get("release_date", {}).get("date", "")
        release_date = None
        try:
            release_date = datetime.strptime(release_raw, "%d %b, %Y").strftime("%Y-%m-%d")
        except:
            release_date = None

        return {
            "appid": appid,
            "name": name,
            "recommendations_total": recommendations,
            "release_date": release_date
        }
    
    @classmethod
    def parse_steamspy(cls, appid):
        url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
        res = requests.get(url).json()
        
        low, high = res["owners"].replace(",", "").split(" .. ")
        owners_low = int(low)
        owners_high = int(high)
        owners_est = (owners_low + owners_high) // 2
        
        # Popularity buckets based on owner estimate
        def owners_bucket(n):
            if n > 50_000_000: return "Very High"
            if n > 5_000_000: return "High"
            if n > 500_000: return "Medium"
            return "Low"
        
        total_reviews = res.get("positive", 0) + res.get("negative", 0)
        
        return {
            "appid": appid,
            "tags": list(res.get("tags", {}).keys()),
            "owners_est": owners_est,
            "owners_low": owners_low,
            "owners_high": owners_high,
            "popularity_bucket": owners_bucket(owners_est),
            "total_reviews": total_reviews,
            "positive_reviews": res.get("positive", 0),
            "negative_reviews": res.get("negative", 0),
            "ccu": res.get("ccu", 0)
        }
    
    @classmethod
    def get_full_metadata(cls, appid):
        meta_store = cls.parse_steam_metadata(appid)
        meta_spy = cls.parse_steamspy(appid)
        return {**meta_store, **meta_spy}
    
    @classmethod
    def build_metadata_dataset(cls):
        rows = []
        for appid in game_appids:
            try:
                row = cls.get_full_metadata(appid)
                rows.append(row)
            except Exception as e:
                print(f"Failed to fetch {appid}: {e}")

        return pd.DataFrame(rows)


class ReviewMetadataHelper:
    @classmethod
    def map_popularity(cls, appid):
        return game_metadata.get(appid, {}).get("popularity_bucket", "Unknown")

    @classmethod
    def release_phase(cls, appid, review_date):
        try:
            release = datetime.strptime(game_metadata[appid]["release_date"], "%Y-%m-%d")
            review = datetime.strptime(review_date, "%Y-%m-%d")
        except:
            return "Unknown"

        diff_months = (review.year - release.year) * 12 + (review.month - release.month)
        if diff_months <= 3:
            return "Launch Period"
        elif diff_months <= 12:
            return "First Year"
        else:
            return "Post-Year"
        
    @classmethod
    def create_preprocess_dataset(cls, df):
        df["popularity_bucket"] = df["GameId"].apply(cls.map_popularity)
        df["release_phase"] = df.apply(
            lambda row: cls.release_phase(row["GameId"], row["DatePosted"]),
            axis=1
        )
        df.to_csv("steam_reviews_cleaned.csv", index=False)


meta_df = GameMetadataHelper.build_metadata_dataset()
game_metadata = meta_df.set_index("appid").to_dict(orient="index")

review_df = ReviewFilteringHelper.preprocess()
ReviewMetadataHelper.create_preprocess_dataset(review_df)
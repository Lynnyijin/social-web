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
    def remove_urls(cls, text):
        return re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)

    @classmethod
    def clean_whitespace(cls, text):
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def clean_text(cls, text):
        text = text.lower()
        text = cls.remove_urls(text)
        text = cls.clean_whitespace(text)
        return text
    
    @classmethod
    def preprocess(cls, appid):
        filename = f"Steam_Reviews_{appid}.csv"
        df = pd.read_csv(filename)
        df = df[df["ReviewText"].fillna("").str.len() > 5]
        df = df[df["ReviewText"].apply(cls.is_english)]
        df = df.drop_duplicates(subset=["ReviewText"])
        df["cleaned_text"] = df["ReviewText"].apply(cls.clean_text)
        df["appid"] = appid
        return df


class GameMetadataHelper:
    @classmethod
    def parse_steam_metadata(cls, appid):
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        res = requests.get(url).json()
        
        data = res[str(appid)]["data"]
        name = data.get("name", "Unknown")
        genres = [g["description"] for g in data.get("genres", [])]
        categories = [c["description"] for c in data.get("categories", [])]
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
            "genres": genres,
            "categories": categories,
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
    def map_genre(cls, appid):
        genres = game_metadata.get(appid, {}).get("genres", ["Unknown"])
        if isinstance(genres, list) and genres:
            return genres[0]
        return "Unknown"

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
        df["genre"] = df["appid"].apply(cls.map_genre)
        df["popularity_bucket"] = df["appid"].apply(cls.map_popularity)
        df["release_phase"] = df.apply(
            lambda row: cls.release_phase(row["appid"], row["DatePosted"]),
            axis=1
        )
        df.to_csv("steam_reviews_cleaned.csv", index=False)


meta_df = GameMetadataHelper.build_metadata_dataset()
game_metadata = meta_df.set_index("appid").to_dict(orient="index")

review_dfs = []
for appid in game_appids:
    df_app = ReviewFilteringHelper.preprocess(appid)
    review_dfs.append(df_app)

df_all = pd.concat(review_dfs, ignore_index=True)
ReviewMetadataHelper.create_preprocess_dataset(df_all)
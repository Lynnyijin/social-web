import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from detoxify import Detoxify
from datetime import datetime

def analyze_csv_with_detoxify(path, model_name="original"):
    df = pd.read_csv(path)
    model = Detoxify(model_name)
    reviews = df["ReviewText"].astype(str).tolist()
    scores = model.predict(reviews) # Returns dictionary with keys ("toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack")

    # Merge each score into dataframe
    for key in scores:
        df[key] = scores[key]

    return df

def parse_review_post_date(df):
    date_posted = df["DatePosted"].astype(str).tolist()
    date_posted_datetime = []
    # Parse review date to standard format if possible
    # Date format on Steam is usually like "Posted: December 1" or "Posted: 1 December"
    # Assume current year if year not provided
    for date in date_posted:
        try:
            parsed_date = datetime.strptime(date.replace('Posted: ', '').strip(), '%B %d')
            parsed_date = parsed_date.replace(year=datetime.now().year)
            date_posted_datetime.append(parsed_date.strftime('%Y-%m-%d'))
        except ValueError:
            try:
                parsed_date = datetime.strptime(date.replace('Posted: ', '').strip(), '%d %B')
                parsed_date = parsed_date.replace(year=datetime.now().year)
                date_posted_datetime.append(parsed_date.strftime('%Y-%m-%d'))
            except ValueError:
                date_posted_datetime.append(None)
    df["DatePosted_Datetime"] = date_posted_datetime
    return df

def get_positive_reviews(df):
    return df[df["IsRecommended"] == True]

def get_negative_reviews(df):
    return df[df["IsRecommended"] == False]

def get_positive_negative_count(df):
    return get_positive_reviews(df).shape[0], get_negative_reviews(df).shape[0]

def plot_toxicity_distribution(df, score="toxicity"):
    plt.figure(figsize=(8,5))
    sns.histplot(df[score], kde=True, bins=30)
    plt.title(f"Distribution of {score.capitalize()} Scores")
    plt.xlabel(score.capitalize())
    plt.ylabel("Count")
    plt.show()

def plot_toxicity_correlation(df):
    toxicity_cols = [
        "toxicity", "severe_toxicity", "obscene",
        "threat", "insult", "identity_attack"
    ]
    
    plt.figure(figsize=(10,7))
    corr = df[toxicity_cols].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm")
    plt.title("Correlation Between Toxicity Categories")
    plt.show()

def plot_toxicity_vs_length(df):
    plt.figure(figsize=(8,6))
    sns.scatterplot(
        x="ReviewLength_Words",
        y="toxicity",
        data=df,
        alpha=0.5
    )
    plt.xlabel("Review Length (words)")
    plt.ylabel("Toxicity Score")
    plt.title("Toxicity vs Review Length")
    plt.show()

def plot_toxicity_by_recommendation(df):
    plt.figure(figsize=(8,6))
    sns.boxplot(
        x="IsRecommended",
        y="toxicity",
        data=df
    )
    plt.title("Toxicity by Review Recommendation")
    plt.xlabel("Is Recommended?")
    plt.ylabel("Toxicity Score")
    plt.show()

def plot_toxicity_over_time(df):
    df = parse_review_post_date(df)
    df["DatePosted_Datetime"] = pd.to_datetime(df["DatePosted_Datetime"], errors="coerce")
    daily = df.groupby(df["DatePosted_Datetime"].dt.date)["toxicity"].mean()

    plt.figure(figsize=(12,6))
    daily.plot()
    plt.title("Average Toxicity Over Time")
    plt.xlabel("Date")
    plt.ylabel("Avg Toxicity")
    plt.xticks(rotation=45)
    plt.show()

def plot_toxicity_vs_playtime(df):
    plt.figure(figsize=(8,6))
    sns.scatterplot(
        x="PlayHours_Numeric",
        y="toxicity",
        data=df,
        alpha=0.5
    )
    plt.title("Toxicity vs Playtime")
    plt.xlabel("Play Time (hours)")
    plt.ylabel("Toxicity")
    plt.show()

if __name__ == "__main__":
    df = analyze_csv_with_detoxify('steam_reviews_cleaned.csv')
    positive_count, negative_count = get_positive_negative_count(df)
    print(f"Positive Reviews: {positive_count}, Negative Reviews: {negative_count}")
    plot_toxicity_distribution(df)
    plot_toxicity_correlation(df)
    plot_toxicity_vs_length(df)
    plot_toxicity_by_recommendation(df)
    plot_toxicity_over_time(df)
    plot_toxicity_vs_playtime(df)
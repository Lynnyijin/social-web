import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from wordcloud import WordCloud

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
    df["DatePosted"] = date_posted_datetime
    return df

# Plotting functions
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
    df["ReviewLength_Words"] = df["ReviewText"].astype(str).apply(lambda x: len(x.split()))
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
        data=df,
        showfliers=False
    )
    plt.title("Toxicity by Review Recommendation")
    plt.xlabel("Is Recommended?")
    plt.ylabel("Toxicity Score")
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

def plot_toxicity_by_genre(df):
    plt.figure(figsize=(10,6))
    sns.boxplot(x="Genre", y="toxicity", data=df, showfliers=False)
    plt.title("Toxicity Scores by Genre")
    plt.xticks(rotation=45)
    plt.show()

def plot_toxicity_by_popularity(df):
    plt.figure(figsize=(10,6))
    sns.boxplot(x="popularity_bucket", y="toxicity", data=df, order=["Very High", "High", "Medium", "Low"], showfliers=False)
    plt.title("Toxicity by Popularity Bucket")
    plt.xticks(rotation=45)
    plt.show()

def plot_helpfulvotes_vs_toxicity(df):
    plt.figure(figsize=(8,6))
    sns.scatterplot(x="HelpfulVotes", y="toxicity", data=df)
    plt.title("Helpful Votes vs Toxicity")
    plt.show()

def wordcloud_by_toxicity(df, score="toxicity", threshold=0.5):
    toxic_text = " ".join(df[df[score] > threshold]["ReviewText"])
    nontoxic_text = " ".join(df[df[score] <= threshold]["ReviewText"])

    plt.figure(figsize=(12,5))
    plt.subplot(1,2,1)
    plt.imshow(WordCloud(background_color="white").generate(toxic_text))
    plt.title("Toxic Reviews")

    plt.subplot(1,2,2)
    plt.imshow(WordCloud(background_color="white").generate(nontoxic_text))
    plt.title("Non-Toxic Reviews")
    plt.show()

def plot_toxicity_binned_by_recommendation(df, bin_size=0.2):
    # Create toxicity bins
    bins = np.arange(0, 1 + bin_size, bin_size)
    labels = [f"{round(bins[i],2)}–{round(bins[i+1],2)}" for i in range(len(bins)-1)]

    df["toxicity_bin"] = pd.cut(
        df["toxicity"],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    # Group by toxicity bin + recommendation
    toxicity_groups = (
        df.groupby(["toxicity_bin", "IsRecommended"])
          .size()
          .reset_index(name="count")
    )

    # Plot
    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=toxicity_groups,
        x="toxicity_bin",
        y="count",
        hue="IsRecommended"
    )

    plt.title("Toxicity Distribution by Recommendation Status")
    plt.xlabel("Toxicity Range")
    plt.ylabel("Number of Reviews")
    plt.legend(title="Is Recommended?")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    df = pd.read_csv('steam_reviews_with_toxicity.csv')
    df = df[df["GameId"] != 3606480]
    
    plot_toxicity_distribution(df, score="toxicity")
    plot_toxicity_correlation(df)
    plot_toxicity_vs_length(df)
    plot_toxicity_by_recommendation(df)
    plot_toxicity_binned_by_recommendation(df)
    plot_toxicity_vs_playtime(df)
    plot_toxicity_by_genre(df)
    plot_toxicity_by_popularity(df)
    plot_helpfulvotes_vs_toxicity(df)
    wordcloud_by_toxicity(df, score="toxicity", threshold=0.5)
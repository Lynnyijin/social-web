import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from detoxify import Detoxify

def analyze_csv_with_detoxify(path, model_name="original"):
    df = pd.read_csv(path)
    model = Detoxify(model_name)
    reviews = df["ReviewText"].astype(str).tolist()
    scores = model.predict(reviews) # Returns dictionary with keys ("toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack")

    # Merge each score into dataframe
    for key in scores:
        df[key] = scores[key]

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

if __name__ == "__main__":
    df = analyze_csv_with_detoxify('Steam_Reviews_1172470_20251202(1).csv')
    positive_count, negative_count = get_positive_negative_count(df)
    print(f"Positive Reviews: {positive_count}, Negative Reviews: {negative_count}")
    plot_toxicity_distribution(df)
    plot_toxicity_correlation(df)
    plot_toxicity_vs_length(df)
    plot_toxicity_by_recommendation(df)
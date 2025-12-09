import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from wordcloud import WordCloud
from scipy.stats import kruskal, mannwhitneyu
import scikit_posthocs as sp

GENRES = ['FPS', 'RPG', 'Indie', 'Strategy', 'Simulation', 'MOBA', 'Multiplayer']
POPULARITY_BUCKETS = ['Low', 'Medium', 'High', 'Very High']

def process_df(df):
    # Remove Specific Game ID
    df = df[df["GameId"] != 3606480]
    df = df.dropna(subset=['toxicity'])
    return df

def print_header(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def kw_across_genres(df):
    print_header("RQ1a: Toxicity Across Game Genres (Kruskal–Wallis)")

    genre_groups = []
    labels_used = []

    for genre in GENRES:
        values = df.loc[df['Genre'] == genre, 'toxicity'].dropna()
        if len(values) > 0:
            genre_groups.append(values)
            labels_used.append(genre)
            print(f"Genre {genre}: n = {len(values)}")

    if len(genre_groups) >= 2:
        H_stat, p_value = kruskal(*genre_groups)
        print(f"\nKruskal–Wallis H = {H_stat:.4f}, p = {p_value:.4e}")
    else:
        print("Not enough non-empty genre groups to run Kruskal–Wallis.")

    # Optional Dunn post-hoc test (pairwise between genres)
    if len(genre_groups) >= 2:
        print("\nDunn post-hoc test between genres (Bonferroni corrected p-values):")
        dunn_genre = sp.posthoc_dunn(
            df[['Genre', 'toxicity']],
            val_col='toxicity',
            group_col='Genre',
            p_adjust='bonferroni'
        )
        print(dunn_genre.loc[labels_used, labels_used])

def kw_across_popularity(df):
    print_header("RQ1b: Toxicity Across Popularity Buckets (Kruskal–Wallis)")

    pop_groups = []
    pop_labels_used = []

    for b in POPULARITY_BUCKETS:
        values = df.loc[df['popularity_bucket'] == b, 'toxicity'].dropna()
        if len(values) > 0:
            pop_groups.append(values)
            pop_labels_used.append(b)
            print(f"Bucket {b}: n = {len(values)}")

    if len(pop_groups) >= 2:
        H_stat_pop, p_value_pop = kruskal(*pop_groups)
        print(f"\nKruskal–Wallis H = {H_stat_pop:.4f}, p = {p_value_pop:.4e}")
    else:
        print("Not enough non-empty popularity groups to run Kruskal–Wallis.")

    # Optional Dunn post-hoc test
    if len(pop_groups) >= 2:
        print("\nDunn post-hoc test between popularity buckets (Bonferroni corrected p-values):")
        dunn_pop = sp.posthoc_dunn(
            df[['popularity_bucket', 'toxicity']],
            val_col='toxicity',
            group_col='popularity_bucket',
            p_adjust='bonferroni'
        )
        print(dunn_pop.loc[pop_labels_used, pop_labels_used])

def mw_recommended_vs_not(df):
    print_header("RQ2a: Toxicity by Recommendation Status (Mann–Whitney U)")

    rec_true = df[df['IsRecommended'] == True]['toxicity'].dropna()
    rec_false = df[df['IsRecommended'] == False]['toxicity'].dropna()

    print(f"Recommended (True): n = {len(rec_true)}")
    print(f"Not recommended (False): n = {len(rec_false)}")

    if len(rec_true) > 0 and len(rec_false) > 0:
        U_stat, p_value_u = mannwhitneyu(rec_true, rec_false, alternative='two-sided')
        print(f"\nMann–Whitney U = {U_stat:.4f}, p = {p_value_u:.4e}")

        # Optional: compute rank-biserial effect size
        n1, n2 = len(rec_true), len(rec_false)
        rank_biserial = 1 - (2 * U_stat) / (n1 * n2)
        print(f"Approx. rank-biserial effect size r_rb = {rank_biserial:.4f}")
    else:
        print("Not enough data in one or both groups for Mann–Whitney U.")

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
    df = process_df(df)

    kw_across_genres(df)
    kw_across_popularity(df)
    mw_recommended_vs_not(df)
    
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
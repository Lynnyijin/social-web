from tqdm import tqdm
import pandas as pd
from detoxify import Detoxify

def analyze_csv_with_detoxify(path, model_name="original"):
    df = pd.read_csv(path)
    model = Detoxify(model_name)
    reviews = df["ReviewText"].astype(str).tolist()
    # Divide reviews into batches to avoid memory issues
    batch_size = 128
    scores = {
        "toxicity": [],
        "severe_toxicity": [],
        "obscene": [],
        "threat": [],
        "insult": [],
        "identity_attack": []
    }
    for i in tqdm(range(0, len(reviews), batch_size), desc="Analyzing toxicity"):
        batch_reviews = reviews[i:i+batch_size]
        batch_scores = model.predict(batch_reviews)
        for key in scores:
            scores[key].extend(batch_scores[key])

    # Add scores to dataframe
    for key in scores:
        df[key] = scores[key]
    return df

if __name__ == "__main__":
    df = analyze_csv_with_detoxify('steam_reviews_cleaned.csv')
    df.to_csv('steam_reviews_with_toxicity.csv', index=False)


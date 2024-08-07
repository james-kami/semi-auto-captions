import json
import os
import shutil
import google.generativeai as genai
from scipy.spatial.distance import cosine
import numpy as np

def load_json_data(file_path):
    """Load data from a JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

def configure_api(api_key):
    """Configure the API with the given key."""
    genai.configure(api_key=api_key)

def generate_embedding(description, model="models/text-embedding-004", task_type="SEMANTIC_SIMILARITY"):
    """Generate an embedding for the given text description."""
    try:
        response = genai.embed_content(model=model, content=description, task_type=task_type)
        return np.array(response['embedding'])
    except Exception as e:
        print(f"Failed to generate embedding: {e}")
        return None

def calculate_similarity(video_embedding, category_embeddings):
    """Calculate and return the category index with the lowest cosine distance."""
    similarities = [cosine(video_embedding, cat_emb) for cat_emb in category_embeddings]
    return np.argmin(similarities)  # Return index of the category with the highest similarity (lowest distance)

def move_video_to_category(video_path, category_path):
    """Move the video file to the specified category directory."""
    if not os.path.exists(category_path):
        os.makedirs(category_path)
    shutil.move(video_path, os.path.join(category_path, os.path.basename(video_path)))
    print(f"Moved {video_path} to {category_path}")

def process_videos(video_data, category_embeddings, categories_base_path):
    """Process and categorize videos based on their descriptions."""
    for video in video_data:
        embedding = generate_embedding(video['description'])
        if embedding is not None:
            best_category_idx = calculate_similarity(embedding, category_embeddings)
            target_dir = os.path.join(categories_base_path, f"Category_{best_category_idx + 1}")
            move_video_to_category(video['file'], target_dir)

def main():
    api_key = 'REDACTED'
    configure_api(api_key)
    video_data = load_json_data('video_info.json')
    category_embeddings = [np.array(emb) for emb in load_json_data('category_embeddings.json')]
    categories_base_path = '/home/ubuntu/videos/categories'
    
    process_videos(video_data, category_embeddings, categories_base_path)

if __name__ == "__main__":
    main()

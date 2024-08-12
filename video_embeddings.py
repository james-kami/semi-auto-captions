import json
import os
import shutil
import google.generativeai as genai # type: ignore
from scipy.spatial.distance import cosine # type: ignore
import numpy as np # type: ignore
from dotenv import load_dotenv # type: ignore

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
    similarities = [cosine(video_embedding, cat_emb) if video_embedding is not None and cat_emb is not None else 1 for cat_emb in category_embeddings]
    return np.argmin(similarities)  # Return index of the category with the highest similarity (lowest distance)

def copy_video_to_category(video_path, category_path):
    """Copy the video file to the specified category directory if it doesn't already exist."""
    if not os.path.exists(category_path):
        os.makedirs(category_path)
    target_file_path = os.path.join(category_path, os.path.basename(video_path))
    if not os.path.exists(target_file_path):
        shutil.copy(video_path, target_file_path)
        print(f"Copied {video_path} to {category_path}")
    #else:
        #print(f"File {video_path} already exists in {category_path}")

def save_results_to_file(results, output_file):
    """Save categorization results to a JSON file."""
    with open(output_file, 'w') as file:
        json.dump(results, file, indent=4)

def process_videos(video_data, category_embeddings, categories_base_path):
    """Process and categorize videos based on their descriptions."""
    results = []
    for video in video_data:
        if video['final_description'].strip().lower() == "positive":
            embedding = generate_embedding(video['description'])
            if embedding is not None:
                best_category_idx = calculate_similarity(embedding, category_embeddings)
                target_dir = os.path.join(categories_base_path, f"Category_{best_category_idx + 1}")
                copy_video_to_category(video['file'], target_dir)
                results.append({
                    'video_file': video['file'],
                    'category': f"Category_{best_category_idx + 1}"
                })
    save_results_to_file(results, 'categorization_results.json')

def main():
    load_dotenv()
    api_key = os.getenv('API_KEY_1')
    configure_api(api_key)
    video_data = load_json_data('video_info.json')
    category_embeddings = [np.array(emb) for emb in load_json_data('category_embeddings.json')]
    categories_base_path = '/nfsmain/james_workplace/categorized_videos'
    
    process_videos(video_data, category_embeddings, categories_base_path)

if __name__ == "__main__":
    main()

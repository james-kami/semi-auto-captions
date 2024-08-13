import json
import os
import shutil
import google.generativeai as genai
import numpy as np
from dotenv import load_dotenv

def load_json_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def configure_api(api_key):
    genai.configure(api_key=api_key)

def generate_embedding(description, model="models/text-embedding-004", task_type="SEMANTIC_SIMILARITY"):
    try:
        response = genai.embed_content(model=model, content=description, task_type=task_type)
        return np.array(response['embedding'])
    except Exception as e:
        print(f"Failed to generate embedding: {e}")
        return None

def exclude_specific_categories(description, category_embeddings):
    description_lower = description.lower()

    # Category 1
    if not any(keyword in description_lower for keyword in ["return", "coming home", "arrive home", "enters house", "back home", "house", "home"]):
        if len(category_embeddings) >= 1:
            category_embeddings[0] = -1  

    # Category 2
    if not any(keyword in description_lower for keyword in ["leave", "leaving", "depart", "exit", "go out", "house", "home"]):
        if len(category_embeddings) >= 2:
            category_embeddings[1] = -1  

    # Category 3
    if not any(keyword in description_lower for keyword in ["visitor", "guest", "arrive", "approach", "enter", "ring bell", "doorbell", "knock"]):
        if len(category_embeddings) >= 3:
            category_embeddings[2] = -1  

    # Category 4
    if not any(keyword in description_lower for keyword in ["stairs", "staircase", "upstairs", "downstairs", "steps", "walks past stairs", "climb"]):
        if len(category_embeddings) >= 4:
            category_embeddings[3] = -1 

    # Category 5
    if not any(keyword in description_lower for keyword in ["pet", "dog", "cat", "fetch", "feeding", "petting"]):
        if len(category_embeddings) >= 5:
            category_embeddings[4] = -1  

    # Category 6
    if not any(keyword in description_lower for keyword in ["fight", "fighting"]):
        if len(category_embeddings) >= 6:
            category_embeddings[5] = -1  

    # Category 7
    if not any(keyword in description_lower for keyword in ["eat", "eating", "ate", "meal"]):
        if len(category_embeddings) >= 7:
            category_embeddings[6] = -1 

    # Category 8
    if not any(keyword in description_lower for keyword in ["plant", "watering", "garden"]):
        if len(category_embeddings) >= 8:
            category_embeddings[7] = -1

    # Category 9:
    if not any(keyword in description_lower for keyword in ["phone", "call", "piano", "guitar", "drum", "drums", "book", "books", "reading", "horse", "horses","horseback", "riding", "bike", "bikes", "biking", "run", "runs", "running", "walk", "walking", "jump", "jumps", "jumping", "sleep", "sleeps", "sleeping", "photo", "computer", "photo", "computers"]):
        if len(category_embeddings) >= 9:
            category_embeddings[8] = -1

    # Category 10: 
    if not any(keyword in description_lower for keyword in ["barking", "meowing", "bark", "meow"]):
        if len(category_embeddings) >= 10:
            category_embeddings[9] = -1 

    # Category 11: 
    if not any(keyword in description_lower for keyword in ["door"]):
        if not any(keyword in description_lower for keyword in ["cat", "dog", "pet"]):
            if len(category_embeddings) >= 11:
                category_embeddings[10] = -1 

    # Category 12: 
    if not any(keyword in description_lower for keyword in ["couch"]):
        if not any(keyword in description_lower for keyword in ["cat", "dog", "pet"]):
            if len(category_embeddings) >= 12:
                category_embeddings[11] = -1 

    # Category 13: 
    if not any(keyword in description_lower for keyword in ["mischief", "mess"]):
            if not any(keyword in description_lower for keyword in ["dog", "cat", "pet"]):
                if len(category_embeddings) >= 13:
                    category_embeddings[12] = -1

    # Category 14: Car comes home/leaves home
    if not any(keyword in description_lower for keyword in ["car", "vehicle", "home", "leaves", "back"]):
        if len(category_embeddings) >= 14:
            category_embeddings[13] = -1

    # Category 15: Car parks in the garage
    if not any(keyword in description_lower for keyword in ["car", "vehicle", "park", "garage"]):
        if len(category_embeddings) >= 15:
            category_embeddings[14] = -1

    # Category 16: Car horn honking
    if not any(keyword in description_lower for keyword in ["horn", "honking"]):
        if len(category_embeddings) >= 16:
            category_embeddings[15] = -1

    # Category 17: Types of cars passing by the door, involving car types
    if not any(keyword in description_lower for keyword in ["car", "fire truck", "ambulance", "truck", "police car", "passed", "door"]):
        if len(category_embeddings) >= 17:
            category_embeddings[16] = -1

    # Category 18: Someone approaches the car/someone is stealing the car
    if not any(keyword in description_lower for keyword in ["car", "stealing", "approaches", "theft"]):
        if len(category_embeddings) >= 18:
            category_embeddings[17] = -1

    # Category 19: Door opens
    if not any(keyword in description_lower for keyword in ["door", "open"]):
        if len(category_embeddings) >= 19:
            category_embeddings[18] = -1

    # Category 20: Door closes
    if not any(keyword in description_lower for keyword in ["door", "close", "closed"]):
        if len(category_embeddings) >= 20:
            category_embeddings[19] = -1

    # Category 21: Package delivery
    if not any(keyword in description_lower for keyword in ["package", "parcel", "delivered", "delivery"]):
        if len(category_embeddings) >= 21:
            category_embeddings[20] = -1

    # Category 22: Outdoor garbage collection
    if not any(keyword in description_lower for keyword in ["garbage", "truck", "removal", "waste", "collection"]):
        if len(category_embeddings) >= 22:
            category_embeddings[21] = -1

    # Category 23: Falling event
    if not any(keyword in description_lower for keyword in ["fall", "falling", "trip", "down"]):
        if len(category_embeddings) >= 23:
            category_embeddings[22] = -1

    # Category 24: Getting off the bed event
    if not any(keyword in description_lower for keyword in ["bed", "getting off", "sleep", "rise", "get up"]):
        if len(category_embeddings) >= 24:
            category_embeddings[23] = -1

    # Final check for unmatched categories
    if all(embedding == -1 for embedding in category_embeddings[:24]):
        category_embeddings = [-1] * 24  
        print("No suitable match found. Assigning to Category 25.")



    return category_embeddings


def copy_video_to_category(video_path, category_path):
    os.makedirs(category_path, exist_ok=True)
    target_file_path = os.path.join(category_path, os.path.basename(video_path))
    if not os.path.exists(target_file_path):
        shutil.copy(video_path, target_file_path)
        print(f"Copied {video_path} to {category_path}")

def save_results_to_file(results, output_file):
    """Save categorization results to a JSON file."""
    with open(output_file, 'w') as file:
        json.dump(results, file, indent=4)

def process_videos(video_data, category_embeddings, categories_base_path):
    results = []
    for video in video_data:
        if video['final_description'].strip().lower() == "positive":
            print(f"\nProcessing video: {video['file']}")
            embedding = generate_embedding(video['description'])
            if embedding is not None:
                filtered_category_embeddings = exclude_specific_categories(video['description'], category_embeddings.copy())
                
                best_category_idx = next((i for i, emb in enumerate(filtered_category_embeddings) if emb is not None), -1)

                if best_category_idx == -1:
                    target_dir = os.path.join(categories_base_path, "Category_25")
                    assigned_category = "Category_25"
                else:
                    target_dir = os.path.join(categories_base_path, f"Category_{best_category_idx + 1}")
                    assigned_category = f"Category_{best_category_idx + 1}"
                
                copy_video_to_category(video['file'], target_dir)
                results.append({
                    'video_file': video['file'],
                    'category': assigned_category
                })
                print(f"Assigned category: {assigned_category}")
    save_results_to_file(results, 'categorization_results.json')

def main():
    load_dotenv()
    api_key = os.getenv('API_KEY_1')
    configure_api(api_key)
    video_data = load_json_data('video_info.json')
    category_embeddings = [np.array(emb) for emb in load_json_data('category_embeddings.json')]
    categories_base_path = '/nfsmain/janderson/new_us_region/categorization'
    
    process_videos(video_data, category_embeddings, categories_base_path)

if __name__ == "__main__":
    main()

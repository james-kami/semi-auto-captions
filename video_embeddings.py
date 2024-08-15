import json
import os
import shutil
import re
import google.generativeai as genai # type: ignore
import numpy as np # type: ignore
from dotenv import load_dotenv # type: ignore

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

    # Category 1: Returning home (specific to returning home context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["return", "coming home", "arrive home", "enters house", "back home"]):
        if len(category_embeddings) >= 1:
            category_embeddings[0] = None  

    # Category 2: Leaving home (specific to leaving home context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["leave house", "leaves house", "leave home", "leaves home", "depart", "exit building", "go out"]):
        if len(category_embeddings) >= 2:
            category_embeddings[1] = None  

    # Category 3: Visitor or guest arrival (specific to visitor/guest context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["visitor", "guest", "arrive", "approach", "enter", "ring bell", "doorbell", "knock"]):
        if len(category_embeddings) >= 3:
            category_embeddings[2] = None  

    # Category 4: Stairs interaction (specific to stairs-related activities)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["stairs", "staircase", "upstairs", "downstairs", "steps", "walks past stairs", "climb"]):
        if len(category_embeddings) >= 4:
            category_embeddings[3] = None 

    # Category 5: Pets playing (must involve both pet and playing activity)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["play", "playing"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["dog", "cat", "pet"])):
        if len(category_embeddings) >= 5:
            category_embeddings[4] = None        

    # Category 6: Fighting (specific to fighting context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["fight", "fighting"]):
        if len(category_embeddings) >= 6:
            category_embeddings[5] = None  

    # Category 7: Eating (must involve eating activity)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["eat", "eating", "ate", "meal", "dining", "food"]):
        if len(category_embeddings) >= 7:
            category_embeddings[6] = None 

    # Category 8: Gardening (must involve gardening activities or plants as the main focus)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["watering", "garden", "gardening", "planting"]) or
            (re.search(r'\bpotted plant\b', description_lower) and re.search(r'\b(garden|outdoor|yard)\b', description_lower))):  # Ensure "potted plant" only triggers with gardening context
        if len(category_embeddings) >= 8:
            category_embeddings[7] = None

    # Category 9: Activities (focus on human or specific activities, exclude generic uses)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in [
        "phone", "call", "piano", "guitar", "drum", "drums", "book", "books", 
        "reading", "horse", "horses", "horseback", "riding", "bike", "bikes", 
        "biking", "jogging", "exercise", "jump", "jumping", "sleep", 
        "sleeping", "photo", "computer", "computers"]) and \
       not re.search(r'\brunning(?! water)\b', description_lower):  # Exclude "running water"
        if len(category_embeddings) >= 9:
            category_embeddings[8] = None

    # Category 10: Animal sounds (focus on pet-related sounds)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["barking", "meowing", "bark", "meow"]):
        if len(category_embeddings) >= 10:
            category_embeddings[9] = None 

    # Category 11: Door interaction with pets (must involve interaction between door and pet)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["door", "doors", "doorway", "gate", "entryway"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["dog", "cat", "pet"]) and
            re.search(r'\b(interaction|open|close|through|scratch|paw|bark at)\b', description_lower)):
        if len(category_embeddings) >= 11:
            category_embeddings[10] = None

    # Category 12: Couch interaction with pets (must involve both couch and pet interaction)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["couch"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["cat", "dog", "pet"])):
        if len(category_embeddings) >= 12:
            category_embeddings[11] = None 

    # Category 13: Pet mischief (must involve both pet and mischief)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["mischief", "mess"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["dog", "cat", "pet"])):
        if len(category_embeddings) >= 13:
            category_embeddings[12] = None

    # Category 14: Car comes/leaves home (specific to vehicles returning to or leaving home)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["car", "vehicle"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["arrive", "depart", "back", "leaves", "returns", "comes home", "drives away", "driving"])):
        if len(category_embeddings) >= 14:
            category_embeddings[13] = None

    # Category 15: Car parks in the garage (must involve parking in a garage)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["car", "vehicle", "park", "garage"]):
        if len(category_embeddings) >= 15:
            category_embeddings[14] = None

    # Category 16: Car horn honking (specific to honking)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["horn", "honking"]):
        if len(category_embeddings) >= 16:
            category_embeddings[15] = None

    # Category 17: Types of cars passing by (must involve both a vehicle and passing by or movement context)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["car", "fire truck", "ambulance", "truck", "police car", "vehicle", "motorcycle", "bus"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["passed", "passing", "driving by", "moves past", "goes by", "drives past", "travels past"])):
        if len(category_embeddings) >= 17:
            category_embeddings[16] = None

    # Category 18: Someone approaches/steals car (must involve both car and approach/steal context)
    if not (any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["car"]) and 
            any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["stealing", "approaches", "theft"])):
        if len(category_embeddings) >= 18:
            category_embeddings[17] = None

    # Category 19: Door opens (specific to door opening)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["door", "open"]):
        if len(category_embeddings) >= 19:
            category_embeddings[18] = None

    # Category 20: Door closes (specific to door closing)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["door", "close", "closed"]):
        if len(category_embeddings) >= 20:
            category_embeddings[19] = None

    # Category 21: Package delivery (specific to delivery context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["package", "parcel", "delivered", "delivery"]):
        if len(category_embeddings) >= 21:
            category_embeddings[20] = None

    # Category 22: Outdoor garbage collection (specific to garbage collection context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["garbage", "truck", "removal", "waste", "collection"]):
        if len(category_embeddings) >= 22:
            category_embeddings[21] = None

    # Category 23: Falling event (specific to falling or tripping)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["fall", "falling"]):
        if len(category_embeddings) >= 23:
            category_embeddings[22] = None

    # Category 24: Getting off the bed event (specific to getting off the bed context)
    if not any(re.search(r'\b' + keyword + r'\b', description_lower) for keyword in ["bed", "getting off", "sleep", "rise", "get up"]):
        if len(category_embeddings) >= 24:
            category_embeddings[23] = None

    # Category 25: Catch-all for unmatched categories
    if all(embedding is None for embedding in category_embeddings[:24]):  # All categories are None
        category_embeddings = [None] * 24  # Set all to None except Category 25
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
                
                # Debug: Check if Category 25 should be assigned
                best_category_idx = next((i for i, emb in enumerate(filtered_category_embeddings) if emb is not None), -1)
                print(f"Best category index found: {best_category_idx}")

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

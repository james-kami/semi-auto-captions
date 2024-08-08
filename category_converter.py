import json
import os
import google.generativeai as genai # type: ignore
from dotenv import load_dotenv # type: ignore

def load_categories(file_path):
    """Load category descriptions from a JSON file."""
    with open(file_path, 'r') as file:
        categories = json.load(file)
    return categories

def generate_embeddings(categories, api_key):
    """Generate embeddings for a list of text descriptions using the correct API method."""
    genai.configure(api_key=api_key)  # Configure API key as previously set up
    embeddings = []
    for text in categories:
        try:
            # Adjust the task_type according to the specific use of the embedding
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="SEMANTIC_SIMILARITY"
            )
            if 'embedding' in response:
                embeddings.append(response['embedding'])
            else:
                print(f"No embedding generated for: {text}")
                embeddings.append(None)
        except Exception as e:
            print(f"Failed to generate embedding for text '{text}': {e}")
            embeddings.append(None)
    return embeddings

def save_embeddings(embeddings, output_file):
    """Save the generated embeddings to a JSON file."""
    with open(output_file, 'w') as file:
        json.dump(embeddings, file, indent=4)

def main():
    load_dotenv()
    api_key = os.getenv('API_KEY_1')
    categories_file = '24categories.json'
    output_file = 'category_embeddings.json'
    
    categories = load_categories(categories_file)
    embeddings = generate_embeddings(categories, api_key)
    save_embeddings(embeddings, output_file)
    print("Embeddings have been generated and saved.")

if __name__ == "__main__":
    main()

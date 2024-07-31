import google.generativeai as genai
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import gc
import json
import signal
from dotenv import load_dotenv
from threading import Lock, Event
import logging
import http.client as http_client

# Setup detailed logging for HTTP requests to troubleshoot SSL issues
http_client.HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# Load environment variables
load_dotenv()

# Global variables
duplicate_counter = [0]
PROCESSED_IDS_FILE = 'processed_ids.json'
processed_ids = set()
lock = Lock()

def extract_unique_id(filename):
    """
    Extracts the unique ID from the filename.
    Example: "TNPUSAF-018072-YXCWN_2024Y07M10D15H15M22S00_door_8.jpg" -> "018072"
    """
    return filename.split('-')[1]

def upload_and_process_image(image_file_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Uploading file {image_file_name}...")
            image_file = genai.upload_file(path=image_file_name)
            print(f"Completed upload: {image_file.uri}")

            while image_file.state.name == "PROCESSING":
                print(f'Waiting for image {image_file_name} to be processed.')
                image_file = genai.get_file(image_file.name)

            if image_file.state.name == "FAILED":
                raise ValueError(f"Image processing failed: {image_file_name}")

            print(f'Image processing complete: {image_file.uri}')
            return image_file
        except Exception as e:
            print(f"Error uploading/processing image {image_file_name}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
            else:
                print("Max retries reached. Skipping file.")
                return None

def generate_description(media_file, delay=1):
    try:
        prompt = "Describe this image in detail."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
        print(f"Making LLM inference request for {media_file.name}...")
        response = model.generate_content([prompt, media_file], request_options={"timeout": 300})
        description = response.text
        print(description)

        enhanced_prompt = (
            "You are an advanced image analysis model. Please analyze the following image and determine if it clearly shows an open or closed door. "
            "Respond with 'positive' if the image contains a clear, unobstructed view of an open or closed door. "
            "Respond with 'negative' if the image is upside-down, extreme obstructed, or does not clearly show an open or closed door. "
            "Criteria for 'positive' include: the door must be visible, the state (open or closed), and the door should not be obscured by objects."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 300})
        final_description = response.text
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for image {media_file.name}: {e}")
        return None, None

def process_image(image_file_name, save_dir):
    with lock:
        unique_id = extract_unique_id(image_file_name)
        if unique_id in processed_ids:
            duplicate_counter[0] += 1
            print(f"Duplicate file detected: {image_file_name}. Skipping upload. Total duplicates: {duplicate_counter[0]}")
            return None

        processed_ids.add(unique_id)

    image_file = upload_and_process_image(image_file_name)
    if not image_file:
        return None

    description, final_description = generate_description(image_file)
    if not final_description:
        genai.delete_file(image_file.name)
        print(f"Deleted file {image_file.uri}")
        return None

    category = "negative"
    save_path = ""
    if "positive" in final_description.lower():
        if "open" in description.lower():
            category = "open-door"
        elif "closed" in description.lower():
            category = "close-door"

        if category in ["open-door", "close-door"]:
            category_dir = os.path.join(save_dir, category)
            os.makedirs(category_dir, exist_ok=True)
            save_path = os.path.join(category_dir, os.path.basename(image_file_name))
            shutil.copy(image_file_name, save_path)
            print(f'Saved image to {save_path}')

    genai.delete_file(image_file.name)
    print(f"Deleted file {image_file.uri}")
    return image_file_name, description, final_description, category, save_path

def get_random_files(media_dir, limit=999999999):
    media_files = []
    search_counter = 0
    for root, dirs, files in os.walk(media_dir):
        jpg_files = [os.path.join(root, file) for file in files if file.endswith('.jpg')]
        media_files.extend(jpg_files)
        search_counter += 1

    if len(media_files) > limit:
        media_files = random.sample(media_files, limit)

    print(f"Took {search_counter} searches to find new files")
    return media_files

def load_processed_ids(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return set(json.load(file))
    return set()

def save_processed_ids(processed_ids, file_path):
    with open(file_path, 'w') as file:
        json.dump(list(processed_ids), file)

def signal_handler(sig, frame):
    print("Signal received, saving processed IDs...")
    save_processed_ids(processed_ids, PROCESSED_IDS_FILE)
    print("Processed IDs saved. Exiting.")
    exit(0)

def main():
    global processed_ids
    processed_ids = load_processed_ids(PROCESSED_IDS_FILE)
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

    if not GOOGLE_API_KEY:
        print("No GOOGLE_API_KEY found. Please set the API key in the environment or in a .env file.")
        return

    genai.configure(api_key=GOOGLE_API_KEY)

    image_dir = "/nfsshare/zj/fenlei"
    save_dir = "/nfsshare/james_storage/door-tracking"
    os.makedirs(save_dir, exist_ok=True)

    image_files = get_random_files(image_dir)
    print(f"Found {len(image_files)} files.")

    batch_size = 100  # Adjust as needed
    max_workers = 1  # Adjust as needed

    # Process images in batches
    for i in range(0, len(image_files), batch_size):
        with ThreadPoolExecutor(max_workers) as executor:  # Use more workers if necessary
            futures = [executor.submit(process_image, image_file, save_dir) for image_file in image_files[i:i+batch_size]]
            results = []
            for future in as_completed(futures):
                result = future.result()
                if result:
                    image_file_name, description, final_description, category, save_path = result
                    results.append(result)
                    with open('image_info.txt', 'a') as f:
                        f.write(f'File: {image_file_name}\nDescription: {description}\nFinal Description: {final_description}\nCategory: {category}\n\n\n\n\n')
            # Optionally, wait here for all threads to complete
            print(f"Batch {i//batch_size + 1} completed. Processing next batch.")
            time.sleep(3)  # Ensures that there's a pause between batches

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()

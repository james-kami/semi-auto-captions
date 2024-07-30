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

duplicate_counter = [0]
PROCESSED_IDS_FILE = 'processed_ids.json'
processed_ids = set()

def extract_unique_id(filename):
    """
    Extracts the unique ID from the filename.
    Example: "TNPUSAF-018072-YXCWN_2024Y07M10D15H15M22S00_door_8.jpg" -> "018072"
    """
    return filename.split('-')[1]

def upload_and_process_image(image_file_name, delay=1):
    max_retries = 1
    for attempt in range(max_retries):
        try:
            print(f"Uploading file {image_file_name}...")
            image_file = genai.upload_file(path=image_file_name)
            print(f"Completed upload: {image_file.uri}")

            # Wait for the image to be processed
            while image_file.state.name == "PROCESSING":
                print(f'Waiting for image {image_file_name} to be processed.')
                time.sleep(10)
                image_file = genai.get_file(image_file.name)

            if image_file.state.name == "FAILED":
                raise ValueError(f"Image processing failed: {image_file_name}")

            print(f'Image processing complete: {image_file.uri}')
            return image_file
        except Exception as e:
            print(f"Error uploading/processing image {image_file_name}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(5)
            else:
                print("Max retries reached. Skipping file.")
                return None
        finally:
            time.sleep(delay)  # Delay to slow down the process

def generate_description(media_file, delay=1):
    try:
        models = list(genai.list_models())
        prompt = "Describe this image in detail."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
        print(f"Making LLM inference request for {media_file.name}...")
        response = model.generate_content([prompt, media_file], request_options={"timeout": 100})
        description = response.text
        print(description)

        enhanced_prompt = (
            "You are an advanced image analysis model. Please analyze the following image and determine if it clearly shows an open or closed door. "
            "Respond with 'positive' if the image contains a clear, unobstructed view of an open or closed door. "
            "Respond with 'negative' if the image is upside-down, extreme obstructed, or does not clearly show an open or closed door. "
            "Criteria for 'positive' include: the door must be visible, the state (open or closed), and the door should not be obscured by objects."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 100})
        final_description = response.text
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for image {media_file.name}: {e}")
        return None, None
    finally:
        time.sleep(delay)  # Delay to slow down the process

def process_image(image_file_name, save_dir, processed_ids, duplicate_counter):
    unique_id = extract_unique_id(image_file_name)
    if unique_id in processed_ids:
        duplicate_counter[0] += 1
        print(f"Duplicate file detected: {image_file_name}. Skipping upload. Total duplicates: {duplicate_counter[0]}")
        return image_file_name, "Duplicate file", None, None, None

    processed_ids.add(unique_id)
    
    try:
        image_file = upload_and_process_image(image_file_name)
        if not image_file:
            return image_file_name, "Error during upload/processing", "Bad file or duplicate", None, None

        description, final_description = generate_description(image_file)
        if not final_description:
            return image_file_name, description, "Error during description generation", None, None

        # Only save the file if it is positively identified as having an open or closed door
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
        
        result = (image_file_name, description, final_description, category, save_path)
        
        genai.delete_file(image_file.name)
        print(f'Deleted file {image_file.uri}')
        
        del image_file, description, final_description
        gc.collect()
        
        return result
    except Exception as e:
        print(f"Exception processing image {image_file_name}: {e}")
        return image_file_name, "Exception occurred", "Bad file or duplicate", "error", ""

def get_random_files(media_dir, limit=1000):
    media_files = []
    search_counter = 0  # Initialize the search counter
    for root, dirs, files in os.walk(media_dir):
        jpg_files = [os.path.join(root, file) for file in files if file.endswith('.jpg')]
        media_files.extend(jpg_files)
        search_counter += 1  # Increment the search counter for each directory searched
    
    if len(media_files) > limit:
        media_files = random.sample(media_files, limit)
    
    print(f"Took {search_counter} searches to find new files")  # Print the search counter
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
    load_dotenv()
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

    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_image = {executor.submit(process_image, image_file, save_dir, processed_ids, duplicate_counter): image_file for image_file in image_files}
        for future in as_completed(future_to_image):
            image_file = future_to_image[future]
            try:
                data = future.result()
                if data:
                    image_file_name, description, final_description, category, save_path = data
                    with open('image_info.txt', 'a') as f:
                        if description and final_description:
                            f.write(f'File: {image_file_name}\n')
                            f.write(f'Description: {description}\n')
                            f.write(f'Final Description: {final_description}\n')
                            f.write(f'Category: {category}\n')
                            f.write(f'Save Path: {save_path}\n\n')
                        else:
                            f.write(f'File: {image_file_name}\n')
                            f.write('Description: Error generating description or processing image.\n')
                            f.write('Final Description: Bad file or duplicate\n\n')
            except Exception as exc:
                print(f'{image_file} generated an exception: {exc}')
                with open('image_info.txt', 'a') as f:
                    f.write(f'File: {image_file}\n')
                    f.write(f'Description: Exception occurred\n')
                    f.write(f'Final Description: {exc}\n\n')

    save_processed_ids(processed_ids, PROCESSED_IDS_FILE)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()

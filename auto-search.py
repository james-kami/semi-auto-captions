import time
import gc
import os
import random
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import google.generativeai as genai

# Load API keys from .env file
load_dotenv()

# List of API keys
API_KEYS = [
    os.getenv("API_KEY_1"),
    os.getenv("API_KEY_2"),
    os.getenv("API_KEY_3"),
    # Add more keys as needed
]
NUM_KEYS = len(API_KEYS)
current_key_index = 0

def get_api_key():
    global current_key_index
    api_key = API_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % NUM_KEYS
    return api_key

def upload_and_process_video(video_file_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            api_key = get_api_key()
            genai.configure(api_key=api_key)

            print(f"Uploading file {video_file_name} using API key: {api_key}...")
            video_file = genai.upload_file(path=video_file_name)
            print(f"Completed upload: {video_file.uri}")

            while video_file.state.name == "PROCESSING":
                print(f'Waiting for video {video_file_name} to be processed.')
                time.sleep(10)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file_name}")

            print(f'Video processing complete: {video_file.uri}')
            return video_file
        except Exception as e:
            print(f"Error uploading/processing video {video_file_name}: {e}")
            if "rate limit" in str(e).lower() or "quota exceeded" in str(e).lower():
                # Switch to the next API key
                get_api_key()
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(5)
            else:
                print("Max retries reached. Skipping file.")
                return None

def generate_description(video_file):
    try:
        api_key = get_api_key()
        genai.configure(api_key=api_key)

        prompt = "Describe this video in detail."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
        print(f"Making LLM inference request for {video_file.name} using API key: {api_key}...")
        response = model.generate_content([prompt, video_file], request_options={"timeout": 10})
        description = response.text
        print(description)

        enhanced_prompt = (
            "You are a video analysis model. Please review the following video description and determine if it contains any significant activities involving people or pets. "
            "IMPORTANT: VIDEO MUST NOT BE STILL UPSIDE-DOWN, OR BLACK SCREEN. "
            "If the video description mentions people or pets performing actions, respond with 'positive'. "
            "If the video is black, grainy, upside-down, or does not mention people or pets, respond with 'negative'."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 10})
        final_description = response.text
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for video {video_file.name}: {e}")
        if "rate limit" in str(e).lower() or "quota exceeded" in str(e).lower():
            # Switch to the next API key
            get_api_key()
        return None, None

def process_video(video_file_name, save_dir):
    try:
        # Upload and process video
        video_file = upload_and_process_video(video_file_name)
        if not video_file:
            return video_file_name, "Error during upload/processing", "Bad file"

        # Generate description
        description, final_description = generate_description(video_file)
        if not final_description:
            return video_file_name, description, "Error during description generation"

        # Save valid video
        if "positive" in final_description.lower():
            save_path = os.path.join(save_dir, os.path.basename(video_file_name))
            shutil.copy(video_file_name, save_path)
            print(f'Saved video to {save_path}')

        result = (video_file_name, description, final_description)
        
        # Delete the file from the server
        genai.delete_file(video_file.name)
        print(f'Deleted file {video_file.uri}')
        
        del video_file, description, final_description
        gc.collect()
        
        return result
    except Exception as e:
        print(f"Exception processing video {video_file_name}: {e}")
        return video_file_name, "Exception occurred", "Bad file"

def get_random_video_files(video_dir, limit):
    us_region_dirs = [os.path.join(video_dir, d) for d in os.listdir(video_dir) if os.path.isdir(os.path.join(video_dir, d))]
    if not us_region_dirs:
        return []

    video_files = []
    for _ in range(limit):
        random_dir = random.choice(us_region_dirs)
        subdirs = [os.path.join(random_dir, d) for d in os.listdir(random_dir) if os.path.isdir(os.path.join(random_dir, d))]
        if not subdirs:
            continue

        random_subdir = random.choice(subdirs)
        files = [os.path.join(random_subdir, f) for f in os.listdir(random_subdir) if f.endswith('.ts') or f.endswith('.mp4')]
        if not files:
            continue

        random_file = random.choice(files)
        video_files.append(random_file)

    return video_files

def main():
    video_dir = "/nfsshare/vidarchives/us_region"
    save_dir = "/nfsshare/james_storage/test2"
    os.makedirs(save_dir, exist_ok=True)

    video_files = get_random_video_files(video_dir, limit=200)

    print(f"Found {len(video_files)} video files.")

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_video = {executor.submit(process_video, video_file, save_dir): video_file for video_file in video_files}
        for future in as_completed(future_to_video):
            video_file = future_to_video[future]
            try:
                data = future.result()
                if data:
                    # Open the file in append mode for each result and write it immediately
                    with open('video_info.txt', 'a') as f:
                        video_file_name, description, final_description = data
                        if description and final_description:
                            f.write(f'File: {video_file_name}\n')
                            f.write(f'Description: {description}\n')
                            f.write(f'Final Description: {final_description}\n\n')
                        else:
                            f.write(f'File: {video_file_name}\n')
                            f.write('Description: Error generating description or processing video.\n')
                            f.write('Final Description: Bad file\n\n')
            except Exception as exc:
                print(f'{video_file} generated an exception: {exc}')
                # Handle exceptions by writing them immediately to the file as well
                with open('video_info.txt', 'a') as f:
                    f.write(f'File: {video_file}\n')
                    f.write(f'Description: Exception occurred\n')
                    f.write(f'Final Description: {exc}\n\n')

if __name__ == "__main__":
    main()

import time
import gc
import os
import random
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Semaphore, Thread
from dotenv import load_dotenv

import google.generativeai as genai

#random.seed(1234)

# Load API keys from .env file
load_dotenv()

# List of API keys
API_KEYS = [
    os.getenv("API_KEY_1"),
    os.getenv("API_KEY_2"),
    os.getenv("API_KEY_3"),
    os.getenv("API_KEY_4"),
    os.getenv("API_KEY_5"),
    # Add more keys as needed
]
NUM_KEYS = len(API_KEYS)

def get_api_key(index):
    return API_KEYS[index % NUM_KEYS]

def upload_video(video_file_name, api_key_index, queue, semaphore):
    max_retries = 1
    api_key = get_api_key(api_key_index)
    genai.configure(api_key=api_key)

    semaphore.acquire()
    try:
        for attempt in range(max_retries):
            try:
                print(f"Attempting to upload {video_file_name}, Attempt {attempt + 1}")
                video_file = genai.upload_file(path=video_file_name)
                print(f"Completed upload: {video_file.uri}")
                queue.put((video_file, api_key_index, video_file_name))
                return  # Successfully uploaded and enqueued
            except Exception as e:
                print(f"Error uploading video {video_file_name} on Attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print("Retrying upload...")
                    time.sleep(1)
                else:
                    print("Max retries reached. Skipping file.")
    finally:
        semaphore.release()
        print(f"Semaphore released for {video_file_name}")

def process_video(queue, save_dir):
    while True:
        video_file = None
        api_key_index = None
        original_file_path = None

        item = queue.get()
        if item is None:
            print("Received None, terminating the processing thread.")
            queue.task_done()
            break  # Stop processing if None is received as a signal to terminate

        video_file, api_key_index, original_file_path = item
        print(f"Processing started for {original_file_path}")

        try:
            # Check the initial state of the video_file
            if not hasattr(video_file, 'state') or not hasattr(video_file.state, 'name'):
                raise AttributeError("Video file object is missing 'state' attributes.")

            # Wait for video processing to complete
            while video_file.state.name == "PROCESSING":
                print(f'Waiting for video {video_file.uri} to be processed...')
                time.sleep(1)
                video_file = genai.get_file(video_file.name)  # Re-fetch the video file status

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.uri}")

            print(f'Video processing completed: {video_file.uri}')

            # Generate description
            description, final_description = generate_description(video_file, api_key_index)
            print(f"Generated descriptions: Brief - {description}, Final - {final_description}")

            if final_description and "positive" in final_description.lower():
                save_path = os.path.join(save_dir, os.path.basename(original_file_path))
                shutil.copy(original_file_path, save_path)
                print(f'Video saved to: {save_path}')

            # Write result to file
            with open('video_info.txt', 'a') as f:
                f.write(f'File: {original_file_path}\n')
                f.write(f'Description: {description}\n')
                f.write(f'Final Description: {final_description}\n\n')

            # Attempt to delete the file from the server
            try:
                genai.delete_file(video_file.name)
                print(f'Deleted file: {video_file.uri}')
            except Exception as e:
                print(f"Failed to delete file {video_file.uri}: {e}")

        except Exception as e:
            print(f"Exception during processing video {original_file_path}: {e}")

        finally:
            queue.task_done()  # Signal that this task is complete
            print(f"Task completed for {original_file_path}")
            del video_file, description, final_description  # Clean up to avoid memory leaks
            gc.collect()  # Collect garbage if there's any unreferenced data




def generate_description(video_file, api_key_index):
    try:
        api_key = get_api_key(api_key_index)
        genai.configure(api_key=api_key)

        prompt = "Describe this video in detail."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
        print(f"Making LLM inference request for {video_file.name} using API key: {api_key}...")
        response = model.generate_content([prompt, video_file], request_options={"timeout": 100})
        description = response.text
        #print(description)

        enhanced_prompt = (
            "You are a video analysis model. Please review the following video description and determine if it contains any significant activities involving people or pets. "
            "IMPORTANT: VIDEO MUST NOT BE STILL UPSIDE-DOWN, OR BLACK SCREEN. "
            "If the video description mentions people or pets performing actions, respond with 'positive'. "
            "If the video is black, grainy, upside-down, or does not mention people or pets, respond with 'negative'."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 100})
        final_description = response.text
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for video {video_file.name}: {e}")
        return None, None

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

    video_files = get_random_video_files(video_dir, limit=16)

    print(f"Found {len(video_files)} video files.")

    # Queue for video processing
    queue = Queue()

    # Semaphore to limit concurrent uploads and processing
    semaphore = Semaphore(4)

    # Start processing thread
    for _ in range(4):  # Number of processing threads
        worker = Thread(target=process_video, args=(queue, save_dir))
        worker.daemon = True
        worker.start()

    # Use ThreadPoolExecutor to upload videos
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, video_file in enumerate(video_files):
            semaphore.acquire()
            executor.submit(upload_video, video_file, index % NUM_KEYS, queue, semaphore)

    queue.join()

if __name__ == "__main__":
    main()

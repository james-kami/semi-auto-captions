import time
import os
import random
import shutil
import json
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import google.generativeai as genai

selected_videos = {}  # keep track of selected videos
processed_videos = {}  # keep track of processed videos

def load_previously_selected_videos(json_log):
    if os.path.exists(json_log):
        with open(json_log, 'r') as f:
            try:
                data = json.load(f)
                return data.get('selected', {}), data.get('processed', {}), data.get('directory_usage', {})
            except (json.JSONDecodeError, ValueError):
                return {}, {}, {}
    return {}, {}, {}

def save_selected_videos(json_log, directory_usage):
    with open(json_log, 'w') as f:
        json.dump({'processed': processed_videos, 'directory_usage': directory_usage}, f, indent=4)

def upload_and_process_video(video_file_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Uploading file {video_file_name}...")
            video_file = genai.upload_file(path=video_file_name)
            print(f"Completed upload: {video_file.uri}")

            while video_file.state.name == "PROCESSING":
                print(f'Waiting for video {video_file_name} to be processed.')
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file_name}")

            print(f'Video processing complete: {video_file.uri}')
            return video_file
        except Exception as e:
            print(f"Error uploading/processing video {video_file_name}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(2)
            else:
                print("Max retries reached. Skipping file.")
                return None

def generate_description(video_file):
    try:
        prompt = "Describe this video in detail."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
        print(f"Making LLM inference request for {video_file.name}...")
        response = model.generate_content([prompt, video_file], request_options={"timeout": 10})
        description = response.text.replace('\n', '')
        print(description)

        enhanced_prompt = (
            "You are a video analysis model. Please review the following video description and determine if it contains any significant activities involving people or pets. "
            "IMPORTANT: VIDEO MUST NOT BE STILL, UPSIDE-DOWN, OR BLACK SCREEN. "
            "If the video description mentions people or pets performing actions, respond with 'positive'. "
            "If the video is black, grainy, upside-down, or does not mention people or pets, respond with 'negative'."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 10})
        final_description = response.text.replace('\n', '')
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for video {video_file.name}: {e}")
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

        # Delete the file from the server
        genai.delete_file(video_file.name)
        print(f'Deleted file {video_file.uri}')
        
        # Record processed video and update JSON
        folder = os.path.dirname(video_file_name)
        if folder not in processed_videos:
            processed_videos[folder] = []
        processed_videos[folder].append(video_file_name)

        return (video_file_name, description, final_description)
    except Exception as e:
        print(f"Exception processing video {video_file_name}: {e}")
        return (video_file_name, "Exception occurred", "Bad file")

def get_random_video_files(video_dir, limit_per_folder, total_limit, max_directory_usage, directory_usage):
    global selected_videos, processed_videos

    all_dirs = [os.path.join(video_dir, d) for d in os.listdir(video_dir) if os.path.isdir(os.path.join(video_dir, d))]
    random.shuffle(all_dirs)  # Shuffle top level directories to vary the selection order

    video_files = []

    for dir_path in all_dirs:
        if len(video_files) >= total_limit:
            break  # Stop if we've reached the total limit for this batch

        if directory_usage.get(dir_path, 0) >= max_directory_usage:
            continue  # Skip this directory if it has reached its usage limit

        subdirs = [os.path.join(dir_path, d) for d in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, d))]
        random.shuffle(subdirs)  # Shuffle subdirectories to further randomize file access

        for subdir in subdirs:
            files = [os.path.join(subdir, f) for f in os.listdir(subdir) if f.endswith('.ts') or f.endswith('.mp4')]
            random.shuffle(files)  # Shuffle files to randomize selection

            eligible_files = [f for f in files if f not in processed_videos.get(subdir, []) and f not in selected_videos.get(subdir, [])]
            count_to_select = min(limit_per_folder, len(eligible_files), total_limit - len(video_files))

            if eligible_files and count_to_select > 0:
                selected_files = random.sample(eligible_files, count_to_select)
                video_files.extend(selected_files)
                selected_videos.setdefault(subdir, []).extend(selected_files)
                directory_usage[dir_path] = directory_usage.get(dir_path, 0) + 1  # Increment usage once per directory accessed per function call

    return video_files, directory_usage

def main():
    global selected_videos, processed_videos
    load_dotenv()
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

    if not GOOGLE_API_KEY:
        print("No GOOGLE_API_KEY found. Please set the API key in the environment or in a .env file.")
        return

    genai.configure(api_key=GOOGLE_API_KEY)

    video_dir = "/nfsshare/vidarchives/us_region"
    save_dir = "/nfsshare/james_storage/test2"
    json_log = 'selected_videos.json'

    # Load previously selected and processed videos and directory usage
    previously_selected_videos, previously_processed_videos, directory_usage = load_previously_selected_videos(json_log)
    selected_videos.update(previously_selected_videos)
    processed_videos.update(previously_processed_videos)

    # Signal handler to save selected videos on interrupt
    def signal_handler(sig, frame):
        print('Interrupted! Must run CLTR+C **2 times** to save progress to JSON file...')
        save_selected_videos(json_log, directory_usage)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    os.makedirs(save_dir, exist_ok=True)

    video_files, directory_usage = get_random_video_files(video_dir, 1, 50, 4, directory_usage)
    print(f"Found {len(video_files)} video files.")

    # Load existing data from video_info.json if it exists
    try:
        with open('video_info.json', 'r') as file:
            existing_results = json.load(file)
    except (IOError, ValueError):
        existing_results = []  # If no file exists or error in reading, start with an empty list

    video_results = existing_results  # Start with existing data
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_video = {executor.submit(process_video, video_file, save_dir): video_file for video_file in video_files}
        for future in as_completed(future_to_video):
            video_file = future_to_video[future]
            try:
                video_file_name, description, final_description = future.result()
                video_results.append({
                    "file": video_file_name,
                    "description": description,
                    "final_description": final_description
                })
            except Exception as exc:
                print(f'{video_file} generated an exception: {exc}')
                video_results.append({
                    "file": video_file,
                    "description": "Exception occurred",
                    "final_description": str(exc)
                })

    # Save updated results to JSON
    with open('video_info.json', 'w') as f:
        json.dump(video_results, f, indent=4)

    # Save the selected and processed videos to JSON file to avoid duplicates in future runs
    save_selected_videos(json_log, directory_usage)

if __name__ == "__main__":
    main()

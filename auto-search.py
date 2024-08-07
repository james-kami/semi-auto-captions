import time
import os
import random
import shutil
import json
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv # type: ignore
from threading import Lock
from itertools import cycle

import google.generativeai as genai # type: ignore

selected_videos = {}  # keep track of selected videos
processed_videos = {}  # keep track of processed videos
end_time = 0

#os.remove("/home/james/semi-auto-captions/video_info.json")
#os.remove("/home/james/semi-auto-captions/selected_videos.json")

def load_previously_selected_videos(json_log):
    if os.path.exists(json_log):
        with open(json_log, 'r') as f:
            try:
                data = json.load(f)
                return data.get('selected', {}), data.get('processed', {}), data.get('directory_usage', {})
            except (json.JSONDecodeError, ValueError):
                return {}, {}, {}
    return {}, {}, {}

def save_run_time(json_file, start_time, end_time, interrupted=False):
    run_time_data = {
        "start_time": start_time,
        "end_time": end_time,
        "elapsed_time": end_time - start_time,
        "interrupted": interrupted
    }
    try:
        with open(json_file, 'r') as file:
            data = json.load(file)
    except (IOError, ValueError):
        data = []  # Initialize as empty list if file doesn't exist or error occurs

    data.append(run_time_data)
    with open(json_file, 'w') as file:
        json.dump(data, file, indent=4)

def save_video_info(json_file, video_results):
    with open(json_file, 'w') as f:
        json.dump(video_results, f, indent=4)

def save_selected_videos(json_log, directory_usage):
    with open(json_log, 'w') as f:
        json.dump({'processed': processed_videos, 'directory_usage': directory_usage}, f, indent=4)

def upload_and_process_video(video_file_name, api_key):
    genai.configure(api_key=api_key)  # Configure API key
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Uploading file {video_file_name}...")
            video_file = genai.upload_file(path=video_file_name)
            print(f"Completed upload: {video_file.uri}")

            while video_file.state.name == "PROCESSING":
                print(f'Waiting for video {video_file_name} to be processed.')
                time.sleep(1.5)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file_name}")

            print(f'Video processing complete: {video_file.uri}')
            return video_file
        except Exception as e:
            print(f"Error uploading/processing video {video_file_name}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(1.5)
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
            "If the video description mentions people or pets performing significant actions, respond with 'positive'. "
            "If the video is black, grainy, upside-down, or does not mention significant actions with people or pets, respond with 'negative'."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 10})
        final_description = response.text.replace('\n', '')
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for video {video_file.name}: {e}")
        return None, None

def process_video(video_file_name, save_dir, api_key):
    try:
        # Ensure api_key is passed correctly here
        video_file = upload_and_process_video(video_file_name, api_key)
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

    print(f"Scanning directory: {video_dir}")

    all_files = []
    for root, dirs, files in os.walk(video_dir):
        for file in files:
            if file.endswith('.ts') or file.endswith('.mp4'):
                all_files.append(os.path.join(root, file))

    print(f"Found video files: {all_files}")

    selected_files = []
    random.shuffle(all_files)  # Shuffle all files to randomize selection

    for file in all_files:
        if len(selected_files) >= total_limit:
            break
        dir_path = os.path.dirname(file)
        if directory_usage.get(dir_path, 0) >= max_directory_usage:
            print(f"Skipping directory {dir_path} due to max usage")
            continue
        if file not in processed_videos and file not in selected_videos:
            selected_files.append(file)
            selected_videos[file] = True
            directory_usage[dir_path] = directory_usage.get(dir_path, 0) + 1  # Increment usage per directory

    return selected_files, directory_usage

def main():
    global selected_videos, processed_videos, end_time
    start_time = time.time()
    load_dotenv()

    # Load multiple API keys
    api_keys = [os.getenv(f'API_KEY_{i}') for i in range(1, 6)]
    if not any(api_keys):
        print("No API keys found. Please set the API keys in the environment.")
        return

    video_dir = "/nfsmain/james_workplace/video_samples"
    save_dir = "/nfsmain/james_workplace/processed_videos"
    json_log = 'selected_videos.json'

    # Load previously selected and processed videos and directory usage
    previously_selected_videos, previously_processed_videos, directory_usage = load_previously_selected_videos(json_log)
    selected_videos.update(previously_selected_videos)
    processed_videos.update(previously_processed_videos)

    # Signal handler to save selected videos on interrupt
    def signal_handler(sig, frame):
        global end_time
        end_time = time.time()  # End timing
        print('Interrupted! Saving progress and preparing to exit...')
        save_selected_videos('selected_videos.json', directory_usage)  # Save progress of selected videos
        save_video_info('video_info.json', video_results)  # Save progress of video info
        save_run_time('script_run_times.json', start_time, end_time, interrupted=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    os.makedirs(save_dir, exist_ok=True)

    # Find 10 files from devices/cameras but not more than 4 files from each device/camera
    video_files, directory_usage = get_random_video_files(video_dir, 10, 10, 10, directory_usage)
    print(f"Found {len(video_files)} video files.")

    # Load existing data from video_info.json if it exists
    try:
        with open('video_info.json', 'r') as file:
            existing_results = json.load(file)
    except (IOError, ValueError):
        existing_results = []  # If no file exists or error in reading, start with an empty list

    video_results = existing_results  # Start with existing data
    with ThreadPoolExecutor(max_workers=len(api_keys)) as executor:
        future_to_video = {}
        api_key_cycle = cycle(api_keys)  # Create a cycle of API keys for round-robin usage

        for video_file in video_files:
            api_key = next(api_key_cycle)  # Get the next API key in the cycle
            future = executor.submit(process_video, video_file, save_dir, api_key)
            future_to_video[future] = video_file

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
    end_time = time.time()
    save_run_time('script_run_times.json', start_time, end_time, interrupted=False)
    print(f"Execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()

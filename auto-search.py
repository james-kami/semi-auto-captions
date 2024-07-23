import google.generativeai as genai
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import gc

def upload_and_process_video(video_file_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Uploading file {video_file_name}...")
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
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(5)
            else:
                print("Max retries reached. Skipping file.")
                return None

def generate_description(video_file):
    try:
        prompt = "Describe this video."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
        print(f"Making LLM inference request for {video_file.name}...")
        response = model.generate_content([prompt, video_file], request_options={"timeout": 600})
        description = response.text
        print(description)

        enhanced_prompt = (
            """You are a model responsible for identifying videos with significant activities involving people or pets. 
            If the video description mentions people or pets doing important actions, respond with 'positive'. 
            If the video is grainy, upside-down, or does not mention people or pets, respond with 'negative'."""
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 600})
        final_description = response.text
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for video {video_file.name}: {e}")
        return None, None

def process_video(video_file_name, save_dir):
    try:
        video_file = upload_and_process_video(video_file_name)
        if not video_file:
            return video_file_name, "Error during upload/processing", "Bad file"

        description, final_description = generate_description(video_file)
        if not final_description:
            return video_file_name, description, "Error during description generation"

        if "positive" in final_description.lower():
            save_path = os.path.join(save_dir, os.path.basename(video_file_name))
            shutil.copy(video_file_name, save_path)
            print(f'Saved video to {save_path}')

        result = (video_file_name, description, final_description)
        
        genai.delete_file(video_file.name)
        print(f'Deleted file {video_file.uri}')
        
        del video_file, description, final_description
        gc.collect()
        
        return result
    except Exception as e:
        print(f"Exception processing video {video_file_name}: {e}")
        return video_file_name, "Exception occurred", "Bad file"

def get_random_video_files(video_dir, limit=10):
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
    userdata = {"GOOGLE_API_KEY": "AIzaSyDuBW39CChEUCrer81fc6YTn-UhtAKwAzA"}
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)

    video_dir = "/nfsshare/vidarchives/us_region"
    save_dir = "/home/james/semi-auto-captions/valid_dataset"
    os.makedirs(save_dir, exist_ok=True)

    video_files = get_random_video_files(video_dir, limit=200)

    print(f"Found {len(video_files)} video files.")

    results = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_video = {executor.submit(process_video, video_file, save_dir): video_file for video_file in video_files}
        for future in as_completed(future_to_video):
            video_file = future_to_video[future]
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as exc:
                print(f'{video_file} generated an exception: {exc}')
                results.append((video_file, "Exception occurred", "Bad file"))

    with open('video_descriptions.txt', 'a') as f:
        for result in results:
            video_file_name, description, final_description = result
            if description and final_description:
                f.write(f'File: {video_file_name}\n')
                f.write(f'Description: {description}\n')
                f.write(f'Final Description: {final_description}\n\n')
            else:
                f.write(f'File: {video_file_name}\n')
                f.write('Description: Error generating description or processing video.\n')
                f.write('Final Description: Bad file\n\n')

if __name__ == "__main__":
    main()
#350

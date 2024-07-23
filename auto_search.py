import google.generativeai as genai
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

def process_video(video_file_name, save_dir):
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
    
    # Generate description
    prompt = "Describe this video."
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
    print(f"Making LLM inference request for {video_file_name}...")
    response = model.generate_content([prompt, video_file], request_options={"timeout": 600})
    description = response.text
    print(description)
    
    # Generate secondary response based on description
    prompt = "If the text contains descriptions of people or pets, give positive, otherwise negative."
    response = model.generate_content([prompt, description], request_options={"timeout": 600})
    final_description = response.text
    print(final_description)
    
    # Save the video if the description contains specific criteria
    if "positive" in final_description.lower():
        save_path = os.path.join(save_dir, os.path.basename(video_file_name))
        shutil.copy(video_file_name, save_path)
        print(f'Saved video to {save_path}')
    
    # Clean up
    genai.delete_file(video_file.name)
    print(f'Deleted file {video_file.uri}')
    
    return final_description

def main():
    userdata = {"GOOGLE_API_KEY": "AIzaSyDuBW39CChEUCrer81fc6YTn-UhtAKwAzA"}
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    
    video_dir = "/home/james/semi-auto-captions/small_dataset"
    save_dir = "/home/james/semi-auto-captions/valid_vids"
    os.makedirs(save_dir, exist_ok=True)
    
    # Collect all .mp4 files in the specified directory and its subdirectories
    video_files = [os.path.join(root, file)
                   for root, _, files in os.walk(video_dir)
                   for file in files if file.endswith('.mp4')]
    
    print(f"Found {len(video_files)} video files.")
    
    # Use ThreadPoolExecutor to process videos in parallel
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_video = {executor.submit(process_video, video_file, save_dir): video_file for video_file in video_files}
        for future in as_completed(future_to_video):
            video_file = future_to_video[future]
            try:
                data = future.result()
                results.append(data)
            except Exception as exc:
                print(f'{video_file} generated an exception: {exc}')
    
    # Save results to a file or further processing
    with open('video_descriptions.txt', 'w') as f:
        for result in results:
            f.write(result + '\n')

if __name__ == "__main__":
    main()

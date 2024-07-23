
# Semi-Automatic Video Annotation

## Overview
This script automates the process of uploading videos to the Google Generative AI platform, processing them, generating descriptions, and saving videos with specific criteria. The results are logged in a text file.

## Prerequisites
- Python 3.9
- Required Python packages: `google.generativeai`, `concurrent.futures`, `shutil`, `gc`, `openpyxl`, and `pandas==1.4.4`
- Google API Key

## Setup
1. **Install necessary packages:**
    ```sh
    pip install google-generativeai
    ...  
    pip install pandas==1.4.4
    ```

2. **Set up environment variables:**
    - Ensure your Google API Key is accessible in the script.

## Configuration - !!! Must edit .py script for paths !!!
- `video_dir`: Directory containing the video files to be processed.
- `save_dir`: Directory where processed videos meeting the criteria will be saved.

## Usage
1. **Place videos in the specified `video_dir` directory.**
2. **Run the script:**
    ```sh
    python auto-search.py
    ```

## Script Workflow
1. **Upload and Process Videos:**
    - Videos are uploaded to the Google Generative AI platform.
    - The script waits for the video processing to complete.
    - If the video processing fails, it retries up to three times.

2. **Generate Descriptions:**
    - Generates an initial description of the video.
    - Enhances the description to detect mentions of people or pets performing significant activities.

3. **Save Valid Videos:**
    - Videos with positive detections are saved to the `save_dir`.

4. **Logging Results:**
    - Descriptions and final determinations are logged in `video_descriptions.txt`.

## Error Handling
- The script handles exceptions during upload, processing, and description generation.
- Videos that encounter errors are logged with an appropriate message.

## Example Execution
```sh
Found 100 video files.
Uploading file video1.mp4...
Completed upload: gs://bucket/video1.mp4
Waiting for video video1.mp4 to be processed.
...
File: video1.mp4
Description: Video of a family picnic.
Final Description: Positive
...

File: video2.mp4
Description: Error generating description or processing video.
Final Description: Bad file
...
```

## Additional Notes
- Adjust the `limit` parameter in `get_random_video_files` to control the number of videos processed. 
- Modify `max_workers` in `ThreadPoolExecutor` to change the level of concurrency. 
- Note: Some form of race conditon or parallel execution bug causes segfaults past two workers for me. Still is pretty fast with two workers.

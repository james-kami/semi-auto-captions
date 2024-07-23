
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
~/semi-auto-captions$ python auto-search.py

Found 200 video files.

Uploading file /nfsshare/vidarchives/us_region/TNPXGAP-765661-TRPGW/20240528/2024Y05M28D14H17M05S00.30.ts...
Uploading file /nfsshare/vidarchives/us_region/TNPXGAV-675905-YCTWZ/20240528/2024Y05M28D07H09M58S00.30.ts...

WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1721775025.989454 1081592 config.cc:230] gRPC experiments enabled: call_status_override_on_cancellation, event_engine_dns, event_engine_listener, http2_stats_fix, monitoring_experiment, pick_first_new, trace_record_callops, work_serializer_clears_time_cache

Completed upload: https://generativelanguage.googleapis.com/v1beta/files/a6jn0w47yce7
Waiting for video /nfsshare/vidarchives/us_region/TNPXGAP-765661-TRPGW/20240528/2024Y05M28D14H17M05S00.30.ts to be processed.

Completed upload: https://generativelanguage.googleapis.com/v1beta/files/yfagj6w134x3
Waiting for video /nfsshare/vidarchives/us_region/TNPXGAV-675905-YCTWZ/20240528/2024Y05M28D07H09M58S00.30.ts to be processed.

Video processing complete: https://generativelanguage.googleapis.com/v1beta/files/a6jn0w47yce7
Making LLM inference request for files/a6jn0w47yce7...
The video shows a black SUV driving down a residential street. The car is driving slowly and appears to be looking for a specific house. The video is likely captured from a home security camera. 
negative 
Deleted file https://generativelanguage.googleapis.com/v1beta/files/a6jn0w47yce7

Video processing complete: https://generativelanguage.googleapis.com/v1beta/files/yfagj6w134x3
Making LLM inference request for files/yfagj6w134x3...
The video shows a car parked on a street at night. The camera is facing the car, and the street is illuminated by a streetlight. The street is cracked and has a yellow stripe painted along the edge. The car's tail lights are visible, as well as part of the rear bumper. There is some green grass growing along the side of the street.  A voice can be heard speaking in a foreign language.  It is unclear what the person is saying. 
negative
Deleted file https://generativelanguage.googleapis.com/v1beta/files/yfagj6w134x3
```

## Additional Notes
- Adjust the `limit` parameter in `get_random_video_files` to control the number of videos processed. 
- Modify `max_workers` in `ThreadPoolExecutor` to change the level of concurrency. 
- Note: Some form of race conditon or parallel execution bug causes segfaults past two workers for me. Still is pretty fast with two workers.

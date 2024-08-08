# ***NOTE***: INFO BELOW IS OUTDATED
# Video Processing System

## Overview
This system is designed to automate the processing of video files, including uploading, processing, and analyzing videos through a generative AI model. It manages video selection from directories, processes them using AI APIs, and saves or deletes files based on analysis results.

## Requirements
- Python 3.x
- Libraries: `os`, `json`, `shutil`, `time`, `concurrent.futures`, `dotenv`, `itertools`, `random`, `signal`, `sys`
- Environment variables for API keys

## Configuration
Ensure that all dependencies are installed using pip:
```
pip install dotenv google-generativeai
```
Set up environment variables for the API keys in a `.env` file as follows:
```
API_KEY_1=<your_api_key_1>
API_KEY_2=<your_api_key_2>
...
API_KEY_5=<your_api_key_5>
```

## Usage
Run the script to process videos in the specified directory:
```
python auto-search.py
```
Interrupt the process safely with CTRL+C to ensure all data is saved correctly.

## Functions

### `load_previously_selected_videos`
Load the selection and processing history from a JSON file to avoid reprocessing.

### `save_selected_videos`
Save the current state of processed and selected videos to a JSON file.

### `upload_and_process_video`
Handles the uploading and initial processing of video files using an external API.

### `generate_description`
Generates descriptions of video content using a generative AI model.

### `process_video`
Coordinates the uploading, processing, and description generation for a single video file.

### `get_random_video_files`
Randomly selects a set number of video files from directories, respecting set limits to prevent overuse.

## Files
- `auto-search.py`: The main Python script.
- `video_info.json`: Stores results from the video processing.
- `selected_videos.json`: Tracks which videos have been processed and selected.

## Note
This system is configured for a specific operational environment and may need adjustments for different API providers or directory structures.

#!/bin/bash

# Script to convert all .ts videos in categorized folders to .mp4 format with optional frame rate.
# The output videos are saved in the same folder as the input videos.
#
# Usage: bash standardize_video.sh [base_folder] [output_format] [fps]

# Default settings
BASE_FOLDER="${1:-/nfsmain/james_workplace/categorized_videos}"
DEFAULT_OUTPUT_FORMAT="mp4"
DEFAULT_FPS="30"

OUTPUT_FORMAT="${2:-$DEFAULT_OUTPUT_FORMAT}"
FPS="${3:-$DEFAULT_FPS}"

# Validate base directory
if [ ! -d "$BASE_FOLDER" ]; then
    echo "Error: Base folder '$BASE_FOLDER' does not exist."
    exit 1
fi

echo "Converting .ts videos in '$BASE_FOLDER' to '$OUTPUT_FORMAT' format with framerate '$FPS' fps."

# Process each category folder
for category_folder in "$BASE_FOLDER"/*; do
    if [[ -d "$category_folder" ]]; then
        echo "Processing category: $(basename "$category_folder")"
        
        # Process each .ts video in the category folder
        for input_video_path in "$category_folder"/*.ts; do
            if [[ -f "$input_video_path" ]]; then
                video_filename=$(basename "$input_video_path")
                video_name="${video_filename%.*}"
                output_video_path="$category_folder/$video_name.$OUTPUT_FORMAT"

                echo "Processing $input_video_path to $output_video_path"
                ffmpeg -y -i "$input_video_path" -filter:v fps=fps=$FPS "$output_video_path"
                if [ $? -eq 0 ]; then
                    echo "Successfully converted $input_video_path to $output_video_path"
                else
                    echo "Failed to convert $input_video_path"
                fi
            fi
        done
    fi
done

#!/bin/bash

# Script to convert all .ts videos in categorized folders to .mp4 format with optional frame rate.
# The output videos are saved in the same folder as the input videos.
#
# Usage: bash standardize_video.sh [base_folder] [output_format] [fps] [num_cores]

# Default settings
BASE_FOLDER="${1:-/nfsmain/james_workplace/categorized_videos}"
DEFAULT_OUTPUT_FORMAT="mp4"
DEFAULT_FPS="30"
DEFAULT_NUM_CORES="$(nproc)"

OUTPUT_FORMAT="${2:-$DEFAULT_OUTPUT_FORMAT}"
FPS="${3:-$DEFAULT_FPS}"
NUM_CORES="${4:-$DEFAULT_NUM_CORES}"

# Validate base directory
if [ ! -d "$BASE_FOLDER" ]; then
    echo "Error: Base folder '$BASE_FOLDER' does not exist."
    exit 1
fi

echo "Converting .ts videos in '$BASE_FOLDER' to '$OUTPUT_FORMAT' format with framerate '$FPS' fps using $NUM_CORES cores."

convert_video() {
    input_video_path="$1"
    output_video_path="${input_video_path%.*}.$OUTPUT_FORMAT"
    
    if [ -f "$output_video_path" ]; then
        echo "Skipping $input_video_path as $output_video_path already exists."
        return
    fi
    
    ffmpeg -y -i "$input_video_path" -filter:v fps=fps=$FPS "$output_video_path"
    if [ $? -eq 0 ]; then
        echo "Successfully converted $input_video_path to $output_video_path"
    else
        echo "Failed to convert $input_video_path"
    fi
}

export -f convert_video
export OUTPUT_FORMAT
export FPS

# Process each category folder
for category_folder in "$BASE_FOLDER"/*; do
    if [[ -d "$category_folder" ]]; then
        echo "Processing category: $(basename "$category_folder")"
        
        # Process each .ts video in the category folder in parallel
        find "$category_folder" -type f -name "*.ts" | parallel -j "$NUM_CORES" convert_video
    fi
done

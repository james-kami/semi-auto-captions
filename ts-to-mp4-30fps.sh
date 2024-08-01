#!/bin/bash

# Script to convert all videos in a default input folder to a desired video format with optional frame rate.
# The output videos are saved in a default output folder, or a specified one.
#
# Usage: bash standardize_video.sh [input_folder] [output_folder] [output_format] [fps]

# Default settings
DEFAULT_INPUT_FOLDER="/nfsshare/james_storage/valid_dataset/input-ts"
DEFAULT_OUTPUT_FOLDER="/nfsshare/james_storage/valid_dataset/output-mp4"
DEFAULT_OUTPUT_FORMAT="mp4"
DEFAULT_FPS="30"

# Parameters handling
INPUT_FOLDER="${1:-$DEFAULT_INPUT_FOLDER}"
OUTPUT_FOLDER="${2:-$DEFAULT_OUTPUT_FOLDER}"
OUTPUT_FORMAT="${3:-$DEFAULT_OUTPUT_FORMAT}"
FPS="${4:-$DEFAULT_FPS}"

# Validate input and output directories
if [ ! -d "$INPUT_FOLDER" ]; then
    echo "Error: Input folder '$INPUT_FOLDER' does not exist."
    exit 1
fi

mkdir -p "$OUTPUT_FOLDER"
if [ ! -d "$OUTPUT_FOLDER" ]; then
    echo "Error: Failed to create output folder '$OUTPUT_FOLDER'."
    exit 1
fi

echo "Converting videos from '$INPUT_FOLDER' to '$OUTPUT_FOLDER' with format '$OUTPUT_FORMAT' and framerate '$FPS' fps."

# Process each video in the input folder
for input_video_path in "$INPUT_FOLDER"/*; do
    if [[ -f "$input_video_path" ]]; then
        video_filename=$(basename "$input_video_path")
        video_name="${video_filename%.*}"
        output_video_path="$OUTPUT_FOLDER/$video_name.$OUTPUT_FORMAT"

        echo "Processing $input_video_path to $output_video_path"
        ffmpeg -y -i "$input_video_path" -filter:v fps=fps=$FPS "$output_video_path"
        if [ $? -eq 0 ]; then
            echo "Successfully converted $input_video_path to $output_video_path"
        else
            echo "Failed to convert $input_video_path"
        fi
    fi
done

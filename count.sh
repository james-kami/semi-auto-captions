#!/bin/bash

# Output file
output_file="ts_files_list.txt"

# Clear the output file if it exists
> "$output_file"

# Create an array to hold all files with their categories
declare -a file_list

# Declare an associative array to store the count of .ts files per category
declare -A file_count

# Iterate over each category directory
for category in /home/ubuntu/semi-auto-captions/videos/category/Category_*; do
    if [ -d "$category" ]; then
        # Get the category name and extract the numerical part
        category_name=$(basename "$category")
        category_number=$(echo "$category_name" | grep -o -E '[0-9]+')

        # Initialize the file count for this category
        file_count["$category_name"]=0

        # Find all .ts files in the category and store them in the array with their category
        while IFS= read -r file; do
            file_list+=("$category_number:$category_name:$file")
            file_count["$category_name"]=$((file_count["$category_name"] + 1))
        done < <(find "$category" -name "*.ts" | sort)
    fi
done

# Sort the array based on the numerical part of the category and the filename timestamps
IFS=$'\n' sorted_file_list=($(sort -t ':' -k1,1n <<<"${file_list[*]}"))

# Write the sorted files to the output file
for item in "${sorted_file_list[@]}"; do
    category_name="${item#*:}"
    category_name="${category_name%%:*}"
    file_path="${item##*:}"
    
    # Write the category name and count if it's different from the last one
    if [ "$last_category" != "$category_name" ]; then
        echo -e "\nCategory: $category_name (${file_count["$category_name"]} files)" >> "$output_file"
        last_category="$category_name"
    fi

    echo "$file_path" >> "$output_file"
done

echo "List of .ts files has been written to $output_file"

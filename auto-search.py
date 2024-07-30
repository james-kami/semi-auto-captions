import google.generativeai as genai
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import gc

def upload_and_process_image(image_file_name):
    """
    Uploads an image file and waits for it to be processed.

    Args:
        image_file_name (str): Path to the image file.

    Returns:
        image_file: The processed image file object or None if failed.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Uploading file {image_file_name}...")
            image_file = genai.upload_file(path=image_file_name)
            print(f"Completed upload: {image_file.uri}")

            # Wait for the image to be processed
            while image_file.state.name == "PROCESSING":
                print(f'Waiting for image {image_file_name} to be processed.')
                time.sleep(10)
                image_file = genai.get_file(image_file.name)

            if image_file.state.name == "FAILED":
                raise ValueError(f"Image processing failed: {image_file_name}")

            print(f'Image processing complete: {image_file.uri}')
            return image_file
        except Exception as e:
            print(f"Error uploading/processing image {image_file_name}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(5)
            else:
                print("Max retries reached. Skipping file.")
                return None

def generate_description(media_file):
    """
    Generates a description for the given media file.

    Args:
        media_file: The media file object.

    Returns:
        tuple: A tuple containing the initial description and the final description.
    """
    try:
        # Initial description prompt
        prompt = "Describe this image in detail."
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
        print(f"Making LLM inference request for {media_file.name}...")
        response = model.generate_content([prompt, media_file], request_options={"timeout": 600})
        description = response.text
        print(description)

        # Enhanced prompt to check for open or closed doors
        enhanced_prompt = (
            "You are an image analysis model. Please review the following image and determine if it clearly shows an open or closed door that is not severely obstructed. "
            "If the image description mentions a clearly open or closed door, respond with 'positive'. "
            "IMPORTANT: If the image is grainy, upside-down, or does not mention a clearly open or closed door, respond with 'negative'."
        )

        response = model.generate_content([enhanced_prompt, description], request_options={"timeout": 600})
        final_description = response.text
        print(final_description)
        return description, final_description
    except Exception as e:
        print(f"Error generating description for image {media_file.name}: {e}")
        return None, None

def process_image(image_file_name, save_dir):
    """
    Processes an image by uploading, generating descriptions, and saving valid images.

    Args:
        image_file_name (str): Path to the image file.
        save_dir (str): Directory to save the processed images.

    Returns:
        tuple: A tuple containing the image file name, description, and final description or error messages.
    """
    try:
        # Upload and process image
        image_file = upload_and_process_image(image_file_name)
        if not image_file:
            return image_file_name, "Error during upload/processing", "Bad file"

        # Generate description
        description, final_description = generate_description(image_file)
        if not final_description:
            return image_file_name, description, "Error during description generation"

        # Save valid image
        if "positive" in final_description.lower():
            save_path = os.path.join(save_dir, os.path.basename(image_file_name))
            shutil.copy(image_file_name, save_path)
            print(f'Saved image to {save_path}')

        result = (image_file_name, description, final_description)
        
        # Delete the file from the server
        genai.delete_file(image_file.name)
        print(f'Deleted file {image_file.uri}')
        
        # Clean up to free memory
        del image_file, description, final_description
        gc.collect()
        
        return result
    except Exception as e:
        print(f"Exception processing image {image_file_name}: {e}")
        return image_file_name, "Exception occurred", "Bad file"

def get_random_files(media_dir, limit=10):
    """
    Retrieves a random selection of image files from the given directory.

    Args:
        media_dir (str): Directory containing media files.
        limit (int): Number of files to retrieve.

    Returns:
        list: List of randomly selected image file paths.
    """
    media_files = []
    for root, dirs, files in os.walk(media_dir):
        jpg_files = [os.path.join(root, file) for file in files if file.endswith('.jpg')]
        media_files.extend(jpg_files)
    
    if len(media_files) > limit:
        media_files = random.sample(media_files, limit)
    
    return media_files

def main():
    """
    Main function to configure the API, process images, and save the results.
    """
    userdata = {"GOOGLE_API_KEY": "AIzaSyDuBW39CChEUCrer81fc6YTn-UhtAKwAzA"}
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)

    image_dir = "/nfsshare/zj/fenlei"
    save_dir = "/nfsshare/james_storage/door-tracking"
    os.makedirs(save_dir, exist_ok=True)

    image_files = get_random_files(image_dir)

    print(f"Found {len(image_files)} files.")

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_image = {executor.submit(process_image, image_file, save_dir): image_file for image_file in image_files}
        for future in as_completed(future_to_image):
            image_file = future_to_image[future]
            try:
                data = future.result()
                if data:
                    # Open the file in append mode for each result and write it immediately
                    with open('image_info.txt', 'a') as f:
                        image_file_name, description, final_description = data
                        if description and final_description:
                            f.write(f'File: {image_file_name}\n')
                            f.write(f'Description: {description}\n')
                            f.write(f'Final Description: {final_description}\n\n')
                        else:
                            f.write(f'File: {image_file_name}\n')
                            f.write('Description: Error generating description or processing image.\n')
                            f.write('Final Description: Bad file\n\n')
            except Exception as exc:
                print(f'{image_file} generated an exception: {exc}')
                # Handle exceptions by writing them immediately to the file as well
                with open('image_info.txt', 'a') as f:
                    f.write(f'File: {image_file}\n')
                    f.write(f'Description: Exception occurred\n')
                    f.write(f'Final Description: {exc}\n\n')

if __name__ == "__main__":
    main()

import os
import uuid
import shutil
from yt_dlp import YoutubeDL
from moviepy.video.io.VideoFileClip import VideoFileClip # type: ignore

def generate_random_filename(extension='mp4'):
    return f"{uuid.uuid4().hex}.{extension}"

def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_youtube_video(url, download_path='/tmp'):
    ensure_directory_exists(download_path)
    random_filename = generate_random_filename()
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(download_path, random_filename),
        'quiet': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        return os.path.join(download_path, random_filename)
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def clip_video(video_path, start_time, duration, output_path='/nfsmain/james_workplace/video_samples/youtube'):
    ensure_directory_exists(output_path)
    try:
        video = VideoFileClip(video_path)
        video_duration = video.duration
        clip_duration = min(duration, video_duration - start_time)
        clipped_video = video.subclip(start_time, start_time + clip_duration)
        random_filename = generate_random_filename()
        output_file = os.path.join(output_path, f'clipped_{random_filename}')
        clipped_video.write_videofile(output_file, codec='libx264')
        return output_file
    except Exception as e:
        print(f"Error processing {video_path}: {e}")
        return None

def process_videos(urls, download_path='/tmp', output_path='/nfsmain/james_workplace/video_samples/youtube'):
    ensure_directory_exists(download_path)
    for url in urls:
        downloaded_path = download_youtube_video(url, download_path)
        if downloaded_path:
            clipped_video_path = clip_video(downloaded_path, start_time=0, duration=20, output_path=output_path)
            if clipped_video_path:
                print(f'Clipped video saved to {clipped_video_path}')
            else:
                print(f"Failed to clip video for {url}")
            os.remove(downloaded_path)  # Remove the original downloaded video
        else:
            print(f"Failed to download video for {url}")

if __name__ == "__main__":
    youtube_urls = [
        'https://www.youtube.com/watch?v=spOZDxBwOEY',
        'https://www.youtube.com/watch?v=xoGjz_xC2aE',
        'https://www.youtube.com/watch?v=x3YYBxN775E',
        'https://www.youtube.com/watch?v=wv1IOnidzQs',
        'https://www.youtube.com/watch?v=bsLJOFq7l0I'
        'https://www.youtube.com/watch?v=FPgm5aWg7qM',


        # Add more URLs as needed
    ]
    process_videos(youtube_urls)

    
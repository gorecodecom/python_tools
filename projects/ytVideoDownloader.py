import os
import re

from moviepy.editor import AudioFileClip
from pytube import YouTube


def get_file_path(directory, file_name_without_extension, file_extension):
    return os.path.join(directory, f"{file_name_without_extension}.{file_extension}")


def is_valid_link(link):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    youtube_regex_match = re.match(youtube_regex, link)
    return youtube_regex_match is not None


def download():
    while True:
        link = input("Enter the link of YouTube video you want to download (or 'exit' to quit): ")
        type = input("Do you want to download as Video or Audio? Enter V for video and A for audio (or 'exit' to quit): ").lower()

        if link.lower() == 'exit' or type == 'exit':
            break

        if not is_valid_link(link):
            print("This does not seem to be a valid YouTube link. Please try again.")
            continue

        yt = YouTube(link)

        if type == 'v':
            yt_resolution = yt.streams.get_highest_resolution()
            print("Downloading video...")
            out_file = yt_resolution.download()
            print(f"Video downloaded at: {out_file}")
        elif type == 'a':
            yt_audio = yt.streams.get_audio_only()
            print("Downloading audio...")
            out_file = yt_audio.download(filename_prefix="audio_")  # save with a different name
            mp3_file_path = get_file_path(os.path.dirname(out_file), "audio_" + yt.title, "mp3")
            audioclip = AudioFileClip(out_file)
            audioclip.write_audiofile(mp3_file_path)
            os.remove(out_file)  # remove the original .webm or .mp4 file
            print(f"Audio downloaded at: {mp3_file_path}")


download()

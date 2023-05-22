from pytube import YouTube
import re


def is_valid_link(link):
    # Prüft, ob der Link ein gültiger YouTube-Link ist
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

        if link.lower() == 'exit':
            break

        if not is_valid_link(link):
            print("This does not seem to be a valid YouTube link. Please try again.")
            continue

        yt = YouTube(link)
        yt_resolution = yt.streams.get_highest_resolution()
        print("Downloading...")
        yt_resolution.download()
        print("Download completed!!")


download()

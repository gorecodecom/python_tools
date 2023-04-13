from pytube import YouTube

def download():
    link = input("Enter the link of YouTube video you want to download: ")
    yt = YouTube(link)
    yt_resolution = yt.streams.get_highest_resolution()
    print("Downloading...")
    yt_resolution.download()
    print("Download completed!!")
    download()

download()
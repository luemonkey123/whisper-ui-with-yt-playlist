import yt_dlp

def get_playlist_video_urls(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'force_generic_extractor': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(playlist_url, download=False)
        print(info_dict)
        video_urls = []
        for entry in info_dict.get('entries', []):
            video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
            video_urls.append(video_url)
        return video_urls

print(get_playlist_video_urls("https://www.youtube.com/watch?v=XX4bJJKg1I0&list=PLpF9Gov2TTAWhxkaOiIWvn_nF8qbqxWhT"))
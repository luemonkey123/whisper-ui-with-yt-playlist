## Many imports
import os
import shutil

import ffmpeg # type: ignore
import gradio as gr # type: ignore
import requests # type: ignore
import yt_dlp # type: ignore
from faster_whisper import WhisperModel # type: ignore
from icecream import ic  # type: ignore
from mutagen.mp3 import MP3  # type: ignore

models = ["small", "small.en", "medium", "medium.en", "large-v3", "turbo", "tiny"]
temp_dir = "temp"
output_dir = "output-files"


def convert_to_mp3(input_file, output_file):
    """Convert any audio file to MP3 format"""
    try:
        ffmpeg.input(input_file).output(
            output_file, format="mp3", audio_bitrate="192k"
        ).run(overwrite_output=True)
        print("Deleting Original")
        os.remove(input_file)
        print(f"Conversion successful: {output_file}")
        return True
    except ffmpeg.Error as e:
        print("Error:", e)
        return False


def get_audio_len(path):
    ## Get the length of an MP3 file w/ mutagen
    audio = MP3(path)
    return audio.info.length


def download_audio(url, output_dir):
    """Download video using yt-dlp and return the file path."""
    os.makedirs(output_dir, exist_ok=True)

    ## yt-dlp options
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
        ],  # Auto convert
    }

    ## Download files and return the path
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.join(output_dir, f"{info['title']}.mp3")


def whisper(audio, model_size, progress=gr.Progress(), call=False):
    cumulative_duration = 0.0  ## Innit the starting duration
    if not call:
        innit()
        progress(0, desc="Starting")

    ## Attempt conversion to .mp3
    if os.path.splitext(audio)[-1] != ".mp3":  ## If file extension is not mp3
        if not convert_to_mp3(audio, f"{''.join(os.path.splitext(audio)[:-1])}.mp3"):
            print("Conversion to mp3 failed")
            return -1

    audio_len = get_audio_len(audio)

    model = WhisperModel(
        model_size, device="cpu", compute_type="int8"
    )  ## Init whisper with settings and model size

    segments, info = model.transcribe(audio, beam_size=5)  ## Get settings and segments
    ic(
        "Detected language '%s' with probability %f"
        % (info.language, info.language_probability)
    )

    with open(f"./{temp_dir}/text/out.txt", "w") as file: ## Open out dir
        for segment in segments: ## Loop through the generater function
            segment_duration = segment.end - segment.start ## The duration is the end - the start
            cumulative_duration += segment_duration ## Add the duration to the cumulative
            progress_value = cumulative_duration / audio_len ## Progress value
            if not call: ## If function is not called, update the progress
                progress(progress_value) 
            print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
            file.write("\n")
            file.write(segment.text)
            yield (segment.text, progress_value) ## Yield for generator function
        file.close()

    with open(f"./{temp_dir}/text/out.txt", "r") as file: ## read the file back as a variable (prob not the most efficiant way)
        content = file.read()
    
    innit(clear_out=False)

    if not call:
        return [content, f"./{temp_dir}/text/out.txt"] ## return the content and out.txt


def get_video_info(video_url):
    ## downloader options
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "force_generic_extractor": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(
            video_url, download=False
        )  ## Just to get the info, not download
        video_title = info_dict.get("title", "No title found")
        thumbnail_url = info_dict.get("thumbnail", "No thumbnail found")
        return video_title, thumbnail_url


def download_thumbnail(thumbnail_url, save_path):
    ## Function is to download a thumbnail given a thumbnail url from yt-dlp
    response = requests.get(thumbnail_url)  ## Use requests library
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)  ## Write the content to the save path


def yt(
    url, model_size, progress=gr.Progress(), call=False
):  ## call is being called by another function, and not used just natively?
    ## Innit folders and progress
    if not call:
        innit()
        progress(0, desc="Downloading and Loading Model")  ## Inform user of start

    info = get_video_info(url)  ## Get Video Info (video title, thumbnail url)

    download_thumbnail(
        info[1], f"./{temp_dir}/thumbnail/test"
    )  # Get the thumbnail ([1] is the thumbnail url)
    download_audio(url, f"./{temp_dir}/audio")  ## Get the audio of the video

    content = []  ## Init content list

    name = os.listdir(f"./{temp_dir}/audio")  ## Get the file name
    os.rename(
        f"./{temp_dir}/audio/{name[0]}", f"./{temp_dir}/audio/audio.mp3"
    )  ## Rename the file to audio.mp3

    ## Whisper Loop (generator)
    for segment in whisper(
        f"./{temp_dir}/audio/audio.mp3", model_size, call=True
    ):  ## Looping through
        if not call:  ## Don't update progress if being called by another function
            progress(segment[1])

        content.append(segment[0])  ## Append the segment to the content list
        yield segment  ## Generator; yield

    content = "\n".join(
        content
    )  ## Join the content list into a str separated by newlines

    innit(clear_out=False)  ## Innit w/o bothering the output files

    ## Return if not being called
    if not call:
        return [
            content,
            f"./{temp_dir}/text/out.txt",
            info[0],
            f"./{temp_dir}/thumbnail/test",
        ]


def get_playlist_video_urls(playlist_url):
    ydl_opts = {
        "quiet": True,
        "extract_flat": False,
        "force_generic_extractor": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(playlist_url, download=False)
        video_urls = []
        for entry in info_dict.get("entries", []):
            video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
            video_urls.append(video_url)
        return video_urls


def yt_playlist(playlist_url, model_size, progress=gr.Progress()):
    ## Getting URLS
    progress(0, desc="Getting URLS")
    vid_urls = get_playlist_video_urls(playlist_url)

    progress(0, desc="Downloading")

    ## Innit progress vars
    total_progress_per_vid = 1 / len(vid_urls)
    cumulative_progress = 0

    ## Looping through the vids
    for counter in range(len(vid_urls)):
        content = []  ## Innit the content list

        ## Loop through the yt generator function (which itself loops through the whisper generator function)
        for i in yt(vid_urls[counter], model_size, call=True):
            vid_progress = i[1]  ## Getting the per vid progress

            ## vid_progress * total_progress_per_vid gets the total progress per vid as of now
            ## + counter * total_progress_per_vid adds what vid its on
            cumulative_progress = (
                vid_progress * total_progress_per_vid + counter * total_progress_per_vid
            )
            progress(cumulative_progress, desc=f"Transcribing Video {counter + 1}")
            content.append(i[0])

        content = "\n".join(
            content
        )  ## Turn the content list into a content str w/ newlines (\n)

        ## Write content to a (new) file
        with open(f"./output-files/out{counter}.txt", "w") as file:
            file.write(content)
            file.close()

    shutil.make_archive(
        f"./{output_dir}/out", "zip", output_dir
    )  ## Make zip out of output files

    out_files = os.listdir(f"./{output_dir}")  ## Get files in the output dir

    ## Delete the zip from the output files
    for file in range(len(out_files)):
        if out_files[file] == "out.zip":
            del out_files[file]
            break

    ## Add file path to the output files list
    for file in range(len(out_files)):
        out_files[file] = f"./{output_dir}/{out_files[file]}"

    innit(clear_out=False)

    ## Return the zip and the files list
    return [f"./{output_dir}/out.zip", out_files]


def innit(clear_out=True):
    ## Remove the temp_dir
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(f"./{temp_dir}")  ## Create the parent temp dir again
    os.mkdir(f"./{temp_dir}/audio")  ## Create the temp audio dir
    os.mkdir(f"./{temp_dir}/text")  ## Create the temp text dir
    os.mkdir(f"./{temp_dir}/thumbnail")  ## Create the temp thumbnail dir

    if clear_out:
        ## Remove then make the output_dir
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        os.mkdir(f"{output_dir}")


innit()

with gr.Blocks() as demo:
    with gr.Tab("YouTube"):
        link = gr.Textbox(label="YT Video Link")
        model_in = gr.Dropdown(label="Model", choices=models)
        tb_title = gr.Label(label="Youtube Title")
        img_thumbnail = gr.Image(label="Youtube Thumbnail")
        output = gr.Textbox(label="Transcribed Text")
        output_file = gr.File(label="Downloadable File Output")
        t_button = gr.Button("Transcribe")
        t_button.click(
            fn=yt,
            inputs=[link, model_in],
            outputs=[output, output_file, tb_title, img_thumbnail],
        )
    with gr.Tab("Youtube Playlist"):
        link = gr.Textbox(label="YT Playlist Link")
        model_in = gr.Dropdown(label="Model", choices=models)
        output_zip = gr.File(label="Downloadable Zip Output")
        output_files = gr.File(label="Downloadable Files Output")
        t_button = gr.Button("Transcribe")
        t_button.click(
            fn=yt_playlist, inputs=[link, model_in], outputs=[output_zip, output_files]
        )
    with gr.Tab("File"):
        audio = gr.Audio(label="File", type="filepath")
        model_in = gr.Dropdown(label="Model", choices=models)
        output = gr.Textbox(label="Transcribed Text")
        output_file = gr.File(label="Downloadable File Output")
        t_button = gr.Button("Transcribe")
        t_button.click(
            fn=whisper, inputs=[audio, model_in], outputs=[output, output_file]
        )

demo.launch(server_name="0.0.0.0", port=7860)

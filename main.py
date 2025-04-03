## Many imports
import math
import os
import shutil

import ffmpeg  # type: ignore
import gradio as gr  # type: ignore
import pysubs2
import requests  # type: ignore
import yt_dlp  # type: ignore
from faster_whisper import WhisperModel  # type: ignore
from icecream import ic  # type: ignore
from mutagen.mp3 import MP3  # type: ignore

models = ["small", "small.en", "medium", "medium.en", "large-v3", "turbo", "tiny"]
temp_dir = "temp"
output_dir = "output-files"
languages = [
    "Auto Detect",
    "en",
    "zh",
    "de",
    "es",
    "ru",
    "ko",
    "fr",
    "ja",
    "pt",
    "tr",
    "pl",
    "ca",
    "nl",
    "ar",
    "sv",
    "it",
    "id",
    "hi",
    "fi",
    "vi",
    "he",
    "uk",
    "el",
    "ms",
    "cs",
    "ro",
    "da",
    "hu",
    "ta",
    "no",
    "th",
    "ur",
    "hr",
    "bg",
    "lt",
    "la",
    "mi",
    "ml",
    "cy",
    "sk",
    "te",
    "fa",
    "lv",
    "bn",
    "sr",
    "az",
    "sl",
    "kn",
    "et",
    "mk",
    "br",
    "eu",
    "is",
    "hy",
    "ne",
    "mn",
    "bs",
    "kk",
    "sq",
    "sw",
    "gl",
    "mr",
    "pa",
    "si",
    "km",
    "sn",
    "yo",
    "so",
    "af",
    "oc",
    "ka",
    "be",
    "tg",
    "sd",
    "gu",
    "am",
    "yi",
    "lo",
    "uz",
    "fo",
    "ht",
    "ps",
    "tk",
    "nn",
    "mt",
    "sa",
    "lb",
    "my",
    "bo",
    "tl",
    "mg",
    "as",
    "tt",
    "haw",
    "ln",
    "ha",
    "ba",
    "jw",
    "su",
]
file_formats = ("txt", "srt", "vtt")


def format_time(seconds):

    hours = math.floor(seconds / 3600)
    seconds %= 3600
    minutes = math.floor(seconds / 60)
    seconds %= 60
    milliseconds = round((seconds - math.floor(seconds)) * 1000)
    seconds = math.floor(seconds)
    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:01d},{milliseconds:03d}"

    return formatted_time


def get_playlist_title(url):
    try:
        ydl_opts = {"quiet": True}  # Suppress output
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", None)
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


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


def srt_to_vtt(input_file, output_file):
    file = pysubs2.load(input_file, encoding="utf-8")
    file.save(output_file, format_="vtt")
    os.remove(input_file)


def generate_subtitle_file(language, srt_list, index=0, name=False):
    if index == 0:
        if name:
            subtitle_file = f"./{output_dir}/{name}.srt"
        else:
            subtitle_file = f"./{output_dir}/out-sub.{language}.srt"
    else:
        if name:
            subtitle_file = f"./{output_dir}/{name}.srt"
        else:
            subtitle_file = f"./{output_dir}/out-sub{index}.{language}.srt"
    text = ""
    for index in range(len(srt_list)):
        segment_start = format_time(srt_list[index][1])
        segment_end = format_time(srt_list[index][2])
        text += f"{str(index+1)} \n"
        text += f"{segment_start} --> {segment_end} \n"
        text += f"{srt_list[index][0]} \n"
        text += "\n"

    f = open(subtitle_file, "w")
    f.write(text)
    f.close()

    return subtitle_file


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


def whisper_gen(audio, model_size, language=None):
    content = []  ## Init initial content list
    cumulative_duration = 0.0  ## Innit the starting duration

    ## Attempt conversion to .mp3
    if os.path.splitext(audio)[-1] != ".mp3":  ## If file extension is not mp3
        if not convert_to_mp3(audio, f"{''.join(os.path.splitext(audio)[:-1])}.mp3"):
            print("Conversion to mp3 failed")
            return -1

    audio_len = get_audio_len(audio)  ## get the length of the audio

    model = WhisperModel(
        model_size, device="cpu", compute_type="int8"
    )  ## Init whisper with settings and model size
    if language is None:
        segments, info = model.transcribe(
            audio, beam_size=5
        )  ## Get settings and segments
    else:
        segments, info = model.transcribe(
            audio, beam_size=5, language=language
        )  ## Get settings and segments with language

    ic(
        "Detected language '%s' with probability %f"
        % (info.language, info.language_probability)
    )

    with open(f"./{temp_dir}/text/out.txt", "w") as file:  ## Open out dir
        for segment in segments:  ## Loop through the generater function
            segment_duration = (
                segment.end - segment.start
            )  ## The duration is the end - the start
            cumulative_duration += (
                segment_duration  ## Add the duration to the cumulative
            )
            progress_value = cumulative_duration / audio_len  ## Progress value

            print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
            file.write("\n")
            file.write(segment.text)  ## Write the text to the file
            content.append(segment.text)  ## Append the text to content
            yield (
                segment,
                progress_value,
                info.language,
            )  ## Yield for generator function


def file(audio, model_size, file_type, language, progress=gr.Progress()):
    innit()

    if language == "Auto Detect":
        language = None

    content = []

    srt_list = []

    for output in whisper_gen(audio, model_size, language):
        language = output[2]
        segment = output[0]
        content.append(segment.text)
        progress(output[1])
        srt_list.append([segment.text, segment.start, segment.end])

    content_str = "\n".join(content)

    if file_type == "txt":
        with open(f"./{output_dir}/out.txt", "w") as file:
            file.write(content_str)

        return (content_str, f"./{output_dir}/out.txt")

    elif file_type == "srt":
        generate_subtitle_file(language, srt_list)

        return (content_str, f"./{output_dir}/out-sub.{language}.srt")

    elif file_type == "vtt":
        generate_subtitle_file(language, srt_list)
        srt_to_vtt(
            f"./{output_dir}/out-sub.{language}.srt",
            f"./{output_dir}/out-sub.{language}.vtt",
        )

        return (content_str, f"./{output_dir}/out-sub.{language}.vtt")


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


def yt_gen(url, model_size, language=None):
    info = get_video_info(url)  ## Get Video Info (video title, thumbnail url)

    download_thumbnail(
        info[1], f"./{temp_dir}/thumbnail/test"
    )  # Get the thumbnail ([1] is the thumbnail url)
    download_audio(url, f"./{temp_dir}/audio")  ## Get the audio of the video

    name = os.listdir(f"./{temp_dir}/audio")  ## Get the file name
    os.rename(
        f"./{temp_dir}/audio/{name[0]}", f"./{temp_dir}/audio/audio.mp3"
    )  ## Rename the file to audio.mp3

    ## Whisper Loop (generator)
    for out in whisper_gen(
        f"./{temp_dir}/audio/audio.mp3", model_size, language
    ):  ## Looping through
        yield out


def yt(url, model_size, file_type, language, use_name, progress=gr.Progress()):
    innit()

    content = []

    srt_list = []

    video_name = get_video_info(url)[0]

    if language == "Auto Detect":
        language = None

    progress(0, desc="Downloading and Loading Model")  ## Inform user of start

    for out in yt_gen(url, model_size, language):
        language = out[2]

        segment = out[0]

        content.append(segment.text)
        srt_list.append([segment.text, segment.start, segment.end])

        progress(out[1])

    content_str = "\n".join(content)

    if file_type == "txt":
        if not use_name:
            with open(f"./{output_dir}/out.txt", "w") as file:
                file.write(content_str)

            return (content_str, f"./{output_dir}/out.txt")
        else:
            with open(f"./{output_dir}/{video_name}.txt", "w") as file:
                file.write(content_str)

            return (content_str, f"./{output_dir}/{video_name}.txt")

    elif file_type == "srt":
        if not use_name:
            generate_subtitle_file(language, srt_list)

            return (content_str, f"./{output_dir}/out-sub.{language}.srt")
        else:
            generate_subtitle_file(language, srt_list, name=video_name)

            return (content_str, f"./{output_dir}/{video_name}.srt")

    elif file_type == "vtt":
        generate_subtitle_file(language, srt_list)

        ic(use_name)

        if not use_name:
            srt_to_vtt(
                f"./{output_dir}/out-sub.{language}.srt",
                f"./{output_dir}/out-sub.{language}.vtt",
            )

            return (content_str, f"./{output_dir}/out-sub.{language}.vtt")
        else:
            srt_to_vtt(
                f"./{output_dir}/out-sub.{language}.srt",
                f"./{output_dir}/{video_name}.vtt",
            )

            return (content_str, f"./{output_dir}/{video_name}.vtt")


def get_yt_meta(url):
    info = get_video_info(url)  ## Get Video Info (video title, thumbnail url)

    download_thumbnail(
        info[1], f"./{temp_dir}/thumbnail/test"
    )  # Get the thumbnail ([1] is the thumbnail url)

    return (info[0], f"./{temp_dir}/thumbnail/test")


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


def yt_playlist(playlist_url, model_size, file_type, language, progress=gr.Progress()):
    innit()

    if language == "Auto Detect":
        language = None

    ## Getting URLS
    progress(0, desc="Getting URLS")
    vid_urls = get_playlist_video_urls(playlist_url)

    ## Innit progress vars
    total_progress_per_vid = 1 / len(vid_urls)
    cumulative_progress = 0

    srt_list = []

    ## Looping through the vids
    for counter in range(len(vid_urls)):
        content = []  ## Innit the content list

        progress(
            counter * total_progress_per_vid, desc=f"Downloading Video {counter + 1}"
        )

        ## Loop through the yt generator function (which itself loops through the whisper generator function)
        for i in yt_gen(vid_urls[counter], model_size, language):
            if language is None:
                language = i[2]

            vid_progress = i[1]  ## Getting the per vid progress

            ## vid_progress * total_progress_per_vid gets the total progress per vid as of now
            ## + counter * total_progress_per_vid adds what vid its on
            cumulative_progress = (
                vid_progress * total_progress_per_vid + counter * total_progress_per_vid
            )
            progress(cumulative_progress, desc=f"Transcribing Video {counter + 1}")

            segment = i[0]
            srt_list.append([segment.text, segment.start, segment.end])

            content.append(segment.text)

        content_str = "\n".join(
            content
        )  ## Turn the content list into a content str w/ newlines (\n)

        ic(counter, language)

        if file_type == "txt":
            ## Write content to a (new) txt file
            with open(f"./output-files/out{counter}.txt", "w") as file:
                file.write(content_str)
                file.close()
        elif file_type == "srt":
            generate_subtitle_file(language, srt_list, counter)

        elif file_type == "vtt":
            generate_subtitle_file(language, srt_list, counter)
            if counter > 0:
                srt_to_vtt(
                    f"./{output_dir}/out-sub{counter}.{language}.srt",
                    f"./{output_dir}/out-sub{counter}.{language}.vtt",
                )
            else:
                srt_to_vtt(
                    f"./{output_dir}/out-sub.{language}.srt",
                    f"./{output_dir}/out-sub.{language}.vtt",
                )

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

        with gr.Row():
            model_in = gr.Dropdown(label="Model", choices=models)
            output_format = gr.Dropdown(
                label="Output File Format", choices=file_formats
            )
            language = gr.Dropdown(label="Language", choices=languages)
            use_name = gr.Checkbox(
                value=True,
                label="Use Original File Name",
                info="If checked, the outputed subtitles file will be named the video name",
            )

        tb_title = gr.Label(label="Youtube Title")
        img_thumbnail = gr.Image(label="Youtube Thumbnail")

        with gr.Row():
            output = gr.Textbox(label="Transcribed Text")
            output_file = gr.File(label="Downloadable File Output")

        t_button = gr.Button("Transcribe")

        link.change(get_yt_meta, inputs=[link], outputs=[tb_title, img_thumbnail])

        t_button.click(
            fn=yt,
            inputs=[link, model_in, output_format, language, use_name],
            outputs=[output, output_file],
        )
    with gr.Tab("Youtube Playlist"):
        link = gr.Textbox(label="YT Playlist Link")
        model_in = gr.Dropdown(label="Model", choices=models)

        with gr.Row():
            output_format = gr.Dropdown(
                label="Output File Format", choices=file_formats
            )
            language = gr.Dropdown(label="Language", choices=languages)

        with gr.Row():
            output_zip = gr.File(label="Downloadable Zip Output")
            output_files = gr.File(label="Downloadable Files Output")

        t_button = gr.Button("Transcribe")
        t_button.click(
            fn=yt_playlist,
            inputs=[link, model_in, output_format, language],
            outputs=[output_zip, output_files],
        )
    with gr.Tab("File"):
        audio = gr.Audio(label="File", type="filepath")

        with gr.Row():
            model_in = gr.Dropdown(label="Model", choices=models)
            output_format = gr.Dropdown(
                label="Output File Format", choices=file_formats
            )
            language = gr.Dropdown(label="Language", choices=languages)

        with gr.Row():
            output = gr.Textbox(label="Transcribed Text", show_copy_button=True)
            output_file = gr.File(label="Downloadable File Output")

        t_button = gr.Button("Transcribe")
        t_button.click(
            file,
            inputs=[audio, model_in, output_format, language],
            outputs=[output, output_file],
        )

demo.queue()

demo.launch()

from django.core.mail import EmailMessage
import threading, os,subprocess, cv2, requests
from django.conf import settings
from urllib.parse import urlparse
from datetime import datetime
from moviepy.editor import VideoFileClip
from tempfile import NamedTemporaryFile
import assemblyai as aai








class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()

class Util:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['email_subject'], body=data['email_body'], to=[data['to_email']])
        EmailThread(email).start()

def download_video(url, id, quality='best'):
    try:
        download_path = os.path.join(f'{settings.BASE_DIR}/media/Youtube/', id)
        subprocess.run(["yt-dlp", "-o", f"{download_path}", url])
        result = subprocess.run(
            ["yt-dlp", "--get-filename", "-o", "%(ext)s", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        video_extension = result.stdout.strip()

        print("Video downloaded successfully!")
        path = download_path.split("media")[1]+f".{video_extension}"
        return path
    except Exception as e:
        print(f"Error downloading video: {e}")

def capture_clip(start_time, end_time, video_url):
    parsed_url = urlparse(video_url)
    path = parsed_url.path
    file_name, file_extension = os.path.splitext(path)

    cap = cv2.VideoCapture(video_url)

    download_path = os.path.join(f'{settings.BASE_DIR}/media/video_clip/', f"{file_name}_{datetime.now()}{file_extension}")
    fourcc = cv2.VideoWriter_fourcc('V', 'P', '9', '0')
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
    output_video = cv2.VideoWriter(download_path, fourcc, frame_rate, (frame_width, frame_height))
    print('output_video================: ', output_video)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        print('current_time: ', current_time)
        if start_time <= end_time:
            output_video.write(frame)

        cap.release()
        output_video.release()

def video_content(url):
    # Download video from the URL
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad responses
    return response.content

def copy_audio_video_clip(input_file, start_time, end_time, is_audio=False):

    parsed_url = urlparse(input_file)
    path = parsed_url.path
    file_name, file_extension = os.path.splitext(os.path.basename(path))
    formatted_timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')
    video_download_path = os.path.join(f'{settings.BASE_DIR}/media/video_clip/', f"{file_name}_{formatted_timestamp}{file_extension}")
    audio_download_path = os.path.join(f'{settings.BASE_DIR}/media/audio_clip/', f"{file_name}_{formatted_timestamp}.mp3")

    video_data = video_content(input_file)

    with NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(video_data)
        temp_file_path = temp_file.name

    try:
        video = VideoFileClip(temp_file_path)
        print(f'Video duration: {video.duration} seconds')

        start_time = int(start_time)
        end_time = int(end_time)
        if end_time > video.duration:
            end_time = video.duration
        if start_time >= end_time:
            raise ValueError('Start time must be less than end time.')

        clip = video.subclip(start_time, end_time)

        if file_extension == '.mp4':
            video_codec = 'libx264'
            audio_codec = 'aac'
        elif file_extension == '.webm':
            video_codec = 'libvpx'
            audio_codec = 'libvorbis'
        elif file_extension == '.ogv':
            video_codec = 'libtheora'
            audio_codec = 'libvorbis'
        else:
            raise ValueError(f'Unsupported file extension: {file_extension}')

        clip.write_videofile(video_download_path, codec=video_codec, audio_codec=audio_codec)
        audio_path = None
        if is_audio:
            audio_clip = clip.audio
            audio_clip.write_audiofile(audio_download_path)
            audio_path = audio_download_path.split("media")[1]
        video_path = video_download_path.split("media")[1]

    finally:
        os.remove(temp_file_path)

    return {"video_clip": video_path, "audio_clip": audio_path}

def transcribe_audio(file_path):

    aai.settings.api_key = "eee3234a75d74ae18caa7dc43fb3585c"
    transcriber = aai.Transcriber()
    config = aai.TranscriptionConfig(speaker_labels=True,language_detection=True,speech_model=aai.SpeechModel.best)


    transcript = transcriber.transcribe(file_path, config)
    print('transcript: ', transcript)

    print("=================",transcript.text)
    return transcript.text

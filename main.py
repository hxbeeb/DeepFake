from flask import Flask, render_template, request, redirect, url_for
import os
from datetime import datetime
import json
from time import time as current_time
import requests
from bs4 import BeautifulSoup
import yt_dlp
import importlib

app = Flask(__name__)

UPLOAD_FOLDER = 'static/videos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

def download_video_from_youtube(video_url, save_path):
    try:
        output_template = os.path.join(save_path, 'downloaded_video.mp4')
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]',
            'outtmpl':output_template
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return output_template, None  # Correct return value
    except Exception as e:
        return None, f"An error occurred: {e}"

def get_video_url_from_x(tweet_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(tweet_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        video_tag = soup.find('video')
        if video_tag and 'src' in video_tag.attrs:
            return video_tag['src']
    return None

def download_video_from_link(video_link, save_path):
    try:
        if 'youtube.com' in video_link or 'youtu.be' in video_link:
            video_path, error_message = download_video_from_youtube(video_link, save_path)
            return video_path, error_message
        elif 'x.com' in video_link:
            file_path,error_message = download_video_from_youtube(video_link,save_path)
            return file_path,error_message
            # if not video_url:
            #     return None, "Failed to extract video URL from X"
            # response = requests.get(video_url, stream=True)
            # if response.status_code != 200:
            #     return None, f"Failed to download video. Status code: {response.status_code}"
            # file_path = os.path.join(save_path, 'downloaded_video.mp4')
            # with open(file_path, 'wb') as f:
            #     for chunk in response.iter_content(chunk_size=8192):
            #         if chunk:
            #             f.write(chunk)
            # return file_path, None
        elif 'instagram.com' in video_link:
            video_path, error_message = download_video_from_youtube(video_link, save_path)
            return video_path, error_message
            # from instaloader import Instaloader, Post
            # L = Instaloader()
            # post = Post.from_shortcode(L.context, video_link.split('/')[-2])
            # video_url = post.video_url
            # response = requests.get(video_url, stream=True)
            # if response.status_code != 200:
            #     return None, f"Failed to download video. Status code: {response.status_code}"
            # file_path = os.path.join(save_path, 'downloaded_video.mp4')
            # with open(file_path, 'wb') as f:
            #     for chunk in response.iter_content(chunk_size=8192):
            #         if chunk:
            #             f.write(chunk)
            # return file_path, None
        else:
            response = requests.get(video_link, stream=True)
            if response.status_code != 200:
                return None, f"Failed to download video. Status code: {response.status_code}"
            file_path = os.path.join(save_path, 'downloaded_video.mp4')
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return file_path, None
    except Exception as e:
        return None, f"An error occurred: {e}"

@app.route('/upload', methods=['POST'])
def upload_file():
    video_link = request.form.get('video_link')
    file = request.files.get('file')

    if not video_link and not file:
        return "No video link or file provided. Please try again."

    video_path = None
    error_message = None

    if video_link:
        video_path, error_message = download_video_from_link(video_link, app.config['UPLOAD_FOLDER'])
    elif file:
        if file.filename == '':
            return "No file selected. Please try again."
        timestamp = int(current_time())
        filename = f"uploaded_video_{timestamp}.mp4"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(video_path)

    if not video_path:
        return f"Failed to download or upload video. {error_message if error_message else 'Please try again.'}"

    video_path2 = os.path.join(app.config['UPLOAD_FOLDER'], "1" + os.path.basename(video_path))

    module = importlib.import_module("deepfake_detector")
    function = getattr(module, "run")

    result_from_det = function(video_path, video_path2)
    print(result_from_det)

    # Get video information
    video_info = {
        'name': os.path.basename(video_path),
        'size': f"{os.path.getsize(video_path) / (1024):.2f} KB",
        'user': 'Guest',
        'source': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'per': result_from_det
    }

    video_info_json = json.dumps(video_info)

    # Redirect to the result page with the video information
    return redirect(url_for('result', video_info=video_info_json, video_path2=video_path2))

@app.route('/result')
def result():
    video_info_json = request.args.get('video_info')
    video_path2 = request.args.get('video_path2')
    print(video_path2)

    video_info = json.loads(video_info_json)
    print(video_info['name'])

    return render_template('result.html', video_url=video_path2, video_info=video_info)

if __name__ == '__main__':
    app.run(debug=True)

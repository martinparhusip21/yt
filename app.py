from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import tempfile

app = Flask(__name__)
CORS(app)

def get_cookies_file():
    """Create temporary cookies file from environment variable"""
    cookies_content = os.environ.get('YOUTUBE_COOKIES', '')
    if cookies_content:
        # Write cookies to temp file
        cookies_path = '/tmp/youtube_cookies.txt'
        with open(cookies_path, 'w') as f:
            f.write(cookies_content)
        return cookies_path
    return None

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "YouTube URL extractor is running"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/get_download_url', methods=['POST'])
def get_download_url():
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        
        if not video_id:
            return jsonify({"error": "video_id is required"}), 400
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        # Add cookies if available
        cookies_file = get_cookies_file()
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url')
            
            if not video_url:
                formats = info.get('formats', [])
                for f in reversed(formats):
                    if f.get('url') and f.get('ext') == 'mp4':
                        video_url = f['url']
                        break
                
                if not video_url and formats:
                    video_url = formats[-1].get('url')
            
            if video_url:
                return jsonify({
                    "success": True,
                    "download_url": video_url,
                    "title": info.get('title', ''),
                    "duration": info.get('duration', 0)
                })
            else:
                return jsonify({"error": "Could not extract video URL"}), 500
                
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/video_info', methods=['POST'])
def video_info():
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        
        if not video_id:
            return jsonify({"error": "video_id is required"}), 400
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        cookies_file = get_cookies_file()
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "success": True,
                "title": info.get('title', ''),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail', ''),
                "channel": info.get('channel', '')
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import re

app = Flask(__name__)
CORS(app)

def is_valid_youtube_url(url):
    pattern = r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
    return re.match(pattern, url) is not None

# Di app.py, tambah logic untuk:
cookies_content = os.environ.get('YOUTUBE_COOKIES', '')
if cookies_content:
    # Tulis ke temp file
    with open('/tmp/cookies.txt', 'w') as f:
        f.write(cookies_content)
    # Pakai di yt-dlp
    ydl_opts['cookiefile'] = '/tmp/cookies.txt'


def extract_video_id(url):
    patterns = [
        r'(?:v=|/)([a-zA-Z0-9_-]{11})(?:[&?]|$)',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "YouTube Download API with yt-dlp"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/get_download_url', methods=['POST'])
def get_download_url():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    try:
        ydl_opts = {
            'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get the direct URL
            video_url = info.get('url')
            
            # If no direct URL, try formats
            if not video_url and info.get('formats'):
                # Find best mp4 format with video+audio
                formats = info['formats']
                
                # Prefer formats with both video and audio
                combined = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4']
                if combined:
                    # Sort by height, prefer 720p
                    combined.sort(key=lambda x: abs((x.get('height') or 0) - 720))
                    video_url = combined[0].get('url')
                
                # Fallback to any mp4 with video
                if not video_url:
                    mp4_videos = [f for f in formats if f.get('vcodec') != 'none' and f.get('ext') == 'mp4']
                    if mp4_videos:
                        mp4_videos.sort(key=lambda x: x.get('height') or 0, reverse=True)
                        video_url = mp4_videos[0].get('url')
            
            if video_url:
                return jsonify({
                    "success": True,
                    "download_url": video_url,
                    "title": info.get('title'),
                    "duration": info.get('duration'),
                    "resolution": info.get('resolution') or info.get('height'),
                })
            else:
                return jsonify({"error": "Could not extract video URL"}), 500
                
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        # Clean up ANSI codes
        import re as re2
        error_msg = re2.sub(r'\x1b\[[0-9;]*m', '', error_msg)
        return jsonify({"error": f"Download error: {error_msg}", "video_url": url}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to process: {str(e)}", "video_url": url}), 500

@app.route('/video_info', methods=['POST'])
def video_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title'),
                "author": info.get('uploader'),
                "length": info.get('duration'),
                "views": info.get('view_count'),
                "description": info.get('description'),
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug_streams', methods=['POST'])
def debug_streams():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            streams = []
            for f in formats:
                streams.append({
                    "format_id": f.get('format_id'),
                    "ext": f.get('ext'),
                    "resolution": f.get('resolution'),
                    "height": f.get('height'),
                    "vcodec": f.get('vcodec'),
                    "acodec": f.get('acodec'),
                    "filesize": f.get('filesize'),
                })
            
            return jsonify({
                "title": info.get('title'),
                "formats_count": len(formats),
                "streams": streams
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

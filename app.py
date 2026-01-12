from flask import Flask, request, jsonify
from flask_cors import CORS
from pytubefix import YouTube
import re

app = Flask(__name__)
CORS(app)  # Enable CORS untuk dipanggil dari Lovable

def is_valid_youtube_url(url):
    """Validate YouTube URL format"""
    patterns = [
        r"^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^(https?://)?(www\.)?youtu\.be/[\w-]+",
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "youtube-downloader"}), 200

@app.route('/get_download_url', methods=['POST'])
def get_download_url():
    """
    Get direct download URL for a YouTube video.
    This is the main endpoint used by Lovable.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    url = data.get('url')
    video_id = data.get('videoId')
    preferred_resolution = data.get('resolution', '720p')
    
    # Build YouTube URL if only videoId provided
    if not url and video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    
    if not url:
        return jsonify({"error": "Missing 'url' or 'videoId' parameter"}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    try:
        yt = YouTube(url)
        
        # Try to get progressive stream (video + audio combined)
        # Progressive streams are easier to process
        stream = None
        
        # Try preferred resolution first
        stream = yt.streams.filter(
            progressive=True, 
            file_extension='mp4', 
            resolution=preferred_resolution
        ).first()
        
        # If not found, try other resolutions in order of preference
        if not stream:
            for res in ['720p', '480p', '360p', '240p', '144p']:
                stream = yt.streams.filter(
                    progressive=True, 
                    file_extension='mp4', 
                    resolution=res
                ).first()
                if stream:
                    break
        
        # Last resort: get any progressive MP4 stream
        if not stream:
            stream = yt.streams.filter(
                progressive=True, 
                file_extension='mp4'
            ).order_by('resolution').desc().first()
        
        if not stream:
            return jsonify({
                "error": "No suitable video stream found",
                "available_streams": [
                    {"resolution": s.resolution, "type": s.mime_type}
                    for s in yt.streams.filter(file_extension='mp4')
                ]
            }), 404
        
        # Return the direct URL
        return jsonify({
            "success": True,
            "download_url": stream.url,
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "resolution": stream.resolution,
            "filesize": stream.filesize,
            "mime_type": stream.mime_type
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to process video: {str(e)}",
            "video_url": url
        }), 500

@app.route('/video_info', methods=['POST'])
def video_info():
    """Get video metadata without download URL"""
    data = request.get_json()
    url = data.get('url')
    video_id = data.get('videoId')
    
    if not url and video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    
    if not url:
        return jsonify({"error": "Missing 'url' or 'videoId' parameter"}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    try:
        yt = YouTube(url)
        
        return jsonify({
            "success": True,
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "views": yt.views,
            "description": yt.description[:500] if yt.description else None,
            "thumbnail_url": yt.thumbnail_url,
            "publish_date": str(yt.publish_date) if yt.publish_date else None,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/available_resolutions', methods=['POST'])
def available_resolutions():
    """Get available video resolutions"""
    data = request.get_json()
    url = data.get('url')
    video_id = data.get('videoId')
    
    if not url and video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    
    if not url:
        return jsonify({"error": "Missing 'url' or 'videoId' parameter"}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    try:
        yt = YouTube(url)
        
        progressive = list(set([
            stream.resolution 
            for stream in yt.streams.filter(progressive=True, file_extension='mp4')
            if stream.resolution
        ]))
        
        all_resolutions = list(set([
            stream.resolution 
            for stream in yt.streams.filter(file_extension='mp4')
            if stream.resolution
        ]))
        
        return jsonify({
            "success": True,
            "progressive": sorted(progressive, key=lambda x: int(x.replace('p', '')), reverse=True),
            "all": sorted(all_resolutions, key=lambda x: int(x.replace('p', '')), reverse=True)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

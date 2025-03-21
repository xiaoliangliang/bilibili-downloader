import re
import os
import requests
import json
import subprocess
from urllib.parse import urlparse, parse_qs

class BilibiliDownloader:
    def __init__(self, cookies=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        }
        # 添加cookie支持
        if cookies:
            self.headers['Cookie'] = cookies
            
        self.ffmpeg_path = 'ffmpeg'  # Make sure ffmpeg is installed and in PATH

    def extract_bvid(self, url):
        """Extract video ID from Bilibili URL"""
        # 处理不同格式的URL
        
        # 检查是否是影视链接 (电影、TV等)
        movie_match = re.search(r'(ss\d+|ep\d+|md\d+)', url)
        if movie_match:
            # 是影视内容，需要先转换成BV号
            media_id = movie_match.group(0)
            print(f"检测到影视内容ID: {media_id}")
            
            # 获取season_id或episode_id
            if media_id.startswith('ss'):
                api_url = f"https://api.bilibili.com/pgc/view/web/season?season_id={media_id[2:]}"
            elif media_id.startswith('ep'):
                api_url = f"https://api.bilibili.com/pgc/view/web/season?ep_id={media_id[2:]}"
            elif media_id.startswith('md'):
                api_url = f"https://api.bilibili.com/pgc/review/user?media_id={media_id[2:]}"
            else:
                raise ValueError("未知的影视内容ID格式")
            
            print(f"请求API: {api_url}")
            response = requests.get(api_url, headers=self.headers)
            data = response.json()
            
            if data['code'] != 0:
                raise Exception(f"获取影视信息失败: {data['message']}")
            
            # 从API响应中提取BV号
            if 'result' in data and 'episodes' in data['result'] and len(data['result']['episodes']) > 0:
                # 获取第一集或当前集的BV号
                bvid = data['result']['episodes'][0].get('bvid')
                if bvid:
                    print(f"成功转换为BV号: {bvid}")
                    return bvid
            
            raise ValueError("无法从影视内容中提取BV号，可能需要会员权限")
        
        # 常规视频BV号提取
        match = re.search(r'BV\w+', url)
        if match:
            return match.group(0)
        
        # AV号处理
        av_match = re.search(r'av(\d+)', url.lower())
        if av_match:
            av_number = av_match.group(1)
            print(f"检测到AV号: {av_number}")
            # 可以选择转换AV号到BV号，或直接使用AV号
            api_url = f"https://api.bilibili.com/x/web-interface/view?aid={av_number}"
            response = requests.get(api_url, headers=self.headers)
            data = response.json()
            
            if data['code'] == 0 and 'data' in data and 'bvid' in data['data']:
                return data['data']['bvid']
        
        # 尝试从URL路径解析
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        for part in path_parts:
            if part.startswith('BV'):
                return part
        
        raise ValueError("无法从URL中提取视频ID，请确认链接格式是否正确")

    def get_video_info(self, bvid):
        """Get video information using BVID"""
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        response = requests.get(api_url, headers=self.headers)
        data = response.json()
        
        if data['code'] != 0:
            raise Exception(f"API error: {data['message']}")
        
        return data['data']

    def get_play_url(self, bvid, cid, quality=120):
        """Get video playback URL"""
        # 使用用户指定的清晰度
        api_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={quality}&fnval=16"
        response = requests.get(api_url, headers=self.headers)
        data = response.json()
        
        if data['code'] != 0:
            raise Exception(f"API error: {data['message']}")
        
        return data['data']

    def download_video(self, url, output_dir='.', quality=120):
        """Download video from Bilibili URL"""
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Extract BVID
        bvid = self.extract_bvid(url)
        print(f"Extracted BVID: {bvid}")
        
        # Get video info
        video_info = self.get_video_info(bvid)
        title = video_info['title'].replace(" ", "_")
        cid = video_info['cid']
        
        # Get playback URL
        play_info = self.get_play_url(bvid, cid, quality)
        
        # Get video and audio URLs
        video_url = None
        audio_url = None
        
        # 尝试获取最高画质视频
        highest_quality = 0
        if play_info.get('dash', {}).get('video'):
            videos = play_info['dash']['video']
            for dash in videos:
                # 选择具有最高id的视频（id数值越大一般代表清晰度越高）
                if dash.get('id', 0) > highest_quality:
                    highest_quality = dash.get('id')
                    video_url = dash['baseUrl']
        
        # 如果找不到dash的视频，尝试获取durl（可能是较旧的视频格式）
        if not video_url and 'durl' in play_info and play_info['durl']:
            video_url = play_info['durl'][0]['url']
        
        # 获取音频
        if play_info.get('dash', {}).get('audio'):
            # 选择码率最高的音频
            highest_audio_bitrate = 0
            for audio in play_info['dash']['audio']:
                if audio.get('bandwidth', 0) > highest_audio_bitrate:
                    highest_audio_bitrate = audio.get('bandwidth')
                    audio_url = audio['baseUrl']
        
        if not video_url:
            raise Exception("Couldn't get video URL")
        
        # Output file paths
        video_path = os.path.join(output_dir, f"{title}_video.mp4")
        audio_path = os.path.join(output_dir, f"{title}_audio.m4a")
        output_path = os.path.join(output_dir, f"{title}.mp4")
        
        # Download video
        print(f"Downloading video: {title}")
        
        if video_url:
            print("Downloading video stream...")
            self._download_file(video_url, video_path)
        
        if audio_url:
            print("Downloading audio stream...")
            self._download_file(audio_url, audio_path)
            
            # Merge audio and video
            print("Merging audio and video...")
            self._merge_audio_video(video_path, audio_path, output_path)
            
            # Clean up temporary files
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        else:
            # If no separate audio, just rename the video file
            os.rename(video_path, output_path)
        
        print(f"Download complete: {output_path}")
        return output_path

    def _download_file(self, url, output_path):
        """Download file with progress indication"""
        response = requests.get(url, headers=self.headers, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        
        with open(output_path, 'wb') as f:
            for data in response.iter_content(block_size):
                f.write(data)
    
    def _merge_audio_video(self, video_path, audio_path, output_path):
        """Merge audio and video using ffmpeg"""
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            output_path
        ]
        subprocess.run(cmd, stderr=subprocess.PIPE)

def main():
    # Create a simple command line interface
    import argparse
    parser = argparse.ArgumentParser(description="Bilibili Video Downloader")
    parser.add_argument("url", help="Bilibili video URL")
    parser.add_argument("--output", "-o", default="D:\\projects\\blibli\\output", help="Output directory")
    # 添加cookie参数
    parser.add_argument("--cookie", "-c", help="Bilibili cookie for premium quality (SESSDATA=xxx; bili_jct=xxx; ...)")
    # 添加清晰度参数
    parser.add_argument("--quality", "-q", type=int, default=120, 
                       help="Video quality (120=4K, 116=1080P60, 112=1080P+, 80=1080P, 74=720P60, 64=720P)")
    args = parser.parse_args()
    
    try:
        downloader = BilibiliDownloader(cookies=args.cookie)
        downloader.download_video(args.url, args.output, args.quality)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
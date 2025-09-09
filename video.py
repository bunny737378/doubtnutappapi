import requests
import re
import json
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class DoubtnutScraper:
    """Scraper for extracting video links from Doubtnut educational content pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_video_url(self, url):
        """
        Extract direct video URL from Doubtnut page
        
        Args:
            url (str): Doubtnut URL to scrape
            
        Returns:
            dict: Result containing success status, video URL, and error info
        """
        try:
            # Validate URL
            if not self._is_valid_doubtnut_url(url):
                return {
                    'success': False,
                    'error': 'Invalid Doubtnut URL format'
                }
            
            # Fetch the page content
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple extraction methods
            video_info = self._extract_from_video_tags(soup) or \
                        self._extract_from_iframe(soup) or \
                        self._extract_from_script_tags(soup) or \
                        self._extract_from_meta_tags(soup)
            
            if video_info:
                return {
                    'success': True,
                    'video_url': video_info['url'],
                    'video_info': video_info
                }
            else:
                return {
                    'success': False,
                    'error': 'No video content found on the page'
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timed out. Please try again.'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Failed to connect to Doubtnut. Check your internet connection.'
            }
        except requests.exceptions.HTTPError as e:
            return {
                'success': False,
                'error': f'HTTP Error: {e.response.status_code}'
            }
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def _is_valid_doubtnut_url(self, url):
        """Validate if URL is from Doubtnut"""
        try:
            parsed = urlparse(url)
            return 'doubtnut.com' in parsed.netloc.lower()
        except:
            return False
    
    def _extract_from_video_tags(self, soup):
        """Extract video URL from HTML5 video tags"""
        video_tags = soup.find_all('video')
        for video in video_tags:
            # Check for src attribute
            if video.get('src'):
                return {
                    'url': video['src'],
                    'type': 'direct_video',
                    'format': self._get_video_format(video['src'])
                }
            
            # Check for source tags within video
            sources = video.find_all('source')
            for source in sources:
                if source.get('src'):
                    return {
                        'url': source['src'],
                        'type': 'direct_video',
                        'format': source.get('type', self._get_video_format(source['src']))
                    }
        return None
    
    def _extract_from_iframe(self, soup):
        """Extract video URL from iframe embeds"""
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if src and any(provider in src.lower() for provider in ['youtube', 'vimeo', 'jwplayer', 'cloudfront']):
                # Handle YouTube embeds
                if 'youtube.com' in src or 'youtu.be' in src:
                    video_id = self._extract_youtube_id(src)
                    if video_id:
                        return {
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'type': 'youtube',
                            'video_id': video_id
                        }
                
                # Handle other video embeds
                return {
                    'url': src,
                    'type': 'iframe_embed',
                    'format': 'embedded'
                }
        return None
    
    def _extract_from_script_tags(self, soup):
        """Extract video URLs from JavaScript/JSON in script tags"""
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_content = script.string
            
            # DOUBTNUT SPECIFIC: Look for videoData in Next.js props
            if 'videoData' in script_content and 'video_name' in script_content:
                try:
                    # Find the JSON structure starting with {"props"
                    start_idx = script_content.find('{"props"')
                    if start_idx != -1:
                        json_str = script_content[start_idx:]
                        data = json.loads(json_str)
                        
                        # Navigate to videoData
                        video_data = data.get('props', {}).get('pageProps', {}).get('videoData', {})
                        video_name = video_data.get('video_name')
                        
                        if video_name:
                            # Construct Doubtnut video URL
                            video_url = f"https://videos.doubtnut.com/{video_name}"
                            
                            # Verify the URL works before returning
                            try:
                                verify_response = self.session.head(video_url, timeout=5)
                                if verify_response.status_code == 200:
                                    return {
                                        'url': video_url,
                                        'type': 'doubtnut_video',
                                        'format': self._get_video_format(video_name),
                                        'duration': video_data.get('duration'),
                                        'question_id': video_data.get('question_id'),
                                        'answer_id': video_data.get('answer_id')
                                    }
                            except:
                                # If verification fails, continue to fallback methods
                                pass
                except:
                    # If JSON parsing fails, continue to fallback methods
                    pass
            
            # FALLBACK: Look for common video URL patterns
            video_patterns = [
                r'"videoUrl":\s*"([^"]+)"',
                r'"video_url":\s*"([^"]+)"',
                r'"src":\s*"([^"]+\.(?:mp4|webm|ogg|m3u8))"',
                r'"file":\s*"([^"]+\.(?:mp4|webm|ogg|m3u8))"',
                r'videoSrc:\s*["\']([^"\']+)["\']',
                r'video:\s*["\']([^"\']+)["\']',
                r'https?://[^"\s]+\.(?:mp4|webm|ogg|m3u8)',
            ]
            
            for pattern in video_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    if self._is_valid_video_url(match):
                        return {
                            'url': match,
                            'type': 'script_extracted',
                            'format': self._get_video_format(match)
                        }
            
            # Try to parse as JSON and look for video URLs
            try:
                # Look for JSON-like structures
                json_matches = re.findall(r'\{[^{}]*(?:"video|src|file")[^{}]*\}', script_content)
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        video_url = self._find_video_in_json(data)
                        if video_url:
                            return {
                                'url': video_url,
                                'type': 'json_extracted',
                                'format': self._get_video_format(video_url)
                            }
                    except:
                        continue
            except:
                pass
        
        return None
    
    def _extract_from_meta_tags(self, soup):
        """Extract video URLs from meta tags (Open Graph, Twitter Card, etc.)"""
        meta_patterns = [
            ('property', 'og:video'),
            ('property', 'og:video:url'),
            ('name', 'twitter:player'),
            ('name', 'twitter:video'),
        ]
        
        for attr, value in meta_patterns:
            meta = soup.find('meta', {attr: value})
            if meta and meta.get('content'):
                url = meta['content']
                if self._is_valid_video_url(url):
                    return {
                        'url': url,
                        'type': 'meta_tag',
                        'format': self._get_video_format(url)
                    }
        return None
    
    def _find_video_in_json(self, data):
        """Recursively find video URLs in JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ['video', 'videourl', 'video_url', 'src', 'file', 'url']:
                    if isinstance(value, str) and self._is_valid_video_url(value):
                        return value
                elif isinstance(value, (dict, list)):
                    result = self._find_video_in_json(value)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_in_json(item)
                if result:
                    return result
        return None
    
    def _is_valid_video_url(self, url):
        """Check if URL appears to be a valid video URL"""
        if not url or not isinstance(url, str):
            return False
        
        # Check for video file extensions
        video_extensions = ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.wmv', '.flv', '.m3u8']
        if any(ext in url.lower() for ext in video_extensions):
            return True
        
        # Check for video hosting domains
        video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'jwplatform.com', 'cloudfront.net']
        if any(domain in url.lower() for domain in video_domains):
            return True
        
        # Check if it starts with http/https
        if url.startswith(('http://', 'https://')):
            return True
        
        return False
    
    def _get_video_format(self, url):
        """Extract video format from URL"""
        if '.mp4' in url.lower():
            return 'video/mp4'
        elif '.webm' in url.lower():
            return 'video/webm'
        elif '.ogg' in url.lower():
            return 'video/ogg'
        elif '.m3u8' in url.lower():
            return 'application/x-mpegURL'
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'vimeo.com' in url:
            return 'vimeo'
        else:
            return 'unknown'
    
    def _extract_youtube_id(self, url):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'youtube\.com/embed/([^/?]+)',
            r'youtube\.com/watch\?v=([^&]+)',
            r'youtu\.be/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

# Command line interface
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python scraper.py <doubtnut_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    scraper = DoubtnutScraper()
    result = scraper.extract_video_url(url)
    
    if result['success']:
        print(f"Success! Video URL: {result['video_url']}")
        if 'video_info' in result:
            print(f"Video Type: {result['video_info'].get('type', 'unknown')}")
            print(f"Format: {result['video_info'].get('format', 'unknown')}")
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

def load_env():
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise ValueError("YouTube API key not found in .env file")
    return api_key

class QuotaExceededException(Exception):
    pass

class RecipeTutorialFinder:
    def __init__(self, api_key=None):  # Accept API key as a parameter
        self.api_key = api_key or load_env()  # Use provided key or load from .env
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.cache_file = 'recipe_cache.json'
        self.quota_file = 'quota_usage.json'
        self.daily_quota_limit = 10000
        self.quota_costs = {'search': 100, 'videos': 1}
        self.top_chefs = {
            'Sanjeev Kapoor': 'UCmoX4QULJ9MB00xW4coMiOw',
            'Ranveer Brar': 'UCEHCRFMycZkNLHjQ1UB0-Pg',
            'Gordon Ramsay': 'UCIEv3lZ_tNXHzL3ox-_uUGQ',
            'Rohit Ghosh' : 'UCGyZg4DZmWyj0q3H3IY15EA',
            'Joshua Weissman' : 'UChBEbMKI1eCcejTtmI32UEw',
            'Chef Ajay Chopra' : 'UCqLJ6XJhCCG_3ehnT6f54dQ',
            'Binging with Babish (Babish Culinary Universe)' : 'UCJHA_jMfCvEnv-3kRjTCQXw',
            'Jamie Oliver' : 'UCpSgg_ECBj25s9moCDfSTsA'
        }
        self.quota_data = self.init_quota_tracking()


    def init_quota_tracking(self):
        if os.path.exists(self.quota_file):
            with open(self.quota_file, 'r') as f:
                quota_data = json.load(f)
                if quota_data.get('date') == datetime.now().date().isoformat():
                    return quota_data
        return {'date': datetime.now().date().isoformat(), 'usage': 0}

    def update_quota_usage(self, operation):
        self.quota_data['usage'] += self.quota_costs.get(operation, 0)
        with open(self.quota_file, 'w') as f:
            json.dump(self.quota_data, f)

    def check_quota_available(self, operation):
        return (self.quota_data['usage'] + self.quota_costs.get(operation, 0)) <= self.daily_quota_limit

    def get_cached_results(self, recipe_name):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                if recipe_name in cache:
                    cached_time = datetime.fromisoformat(cache[recipe_name]['timestamp'])
                    if datetime.now() - cached_time < timedelta(hours=24):
                        return cache[recipe_name]['results']
        return None

    def cache_results(self, recipe_name, results):
        cache = {recipe_name: {'timestamp': datetime.now().isoformat(), 'results': results}}
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f)

    def get_video_details(self, video_ids):
        if not video_ids or not self.check_quota_available('videos'):
            return []
        try:
            response = self.youtube.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids)
            ).execute()
            logging.info(f"API response: {response}")  # Log the API response
            self.update_quota_usage('videos')
            return response.get('items', [])
        except HttpError as e:
            logging.error(f"Error fetching video details: {e}")
            return []

    def search_videos(self, recipe_name):
        if not self.check_quota_available('search'):
            raise QuotaExceededException("API quota exceeded")
        results = []
        for chef, channel_id in self.top_chefs.items():
            if not self.check_quota_available('search'):
                break
            try:
                response = self.youtube.search().list(
                    q=f"{recipe_name} recipe",
                    channelId=channel_id,
                    part='id,snippet',
                    type='video',
                    maxResults=2
                ).execute()
                self.update_quota_usage('search')
                video_ids = [item['id']['videoId'] for item in response.get('items', [])]
                videos = self.get_video_details(video_ids)
                results.extend(self.format_video_data(v, chef) for v in videos)
            except HttpError as e:
                logging.error(f"Error searching videos for {chef}: {e}")
        return results[:5]

    def format_video_data(self, video, chef_name):
        snippet = video.get('snippet', {})
        stats = video.get('statistics', {})
        return {
            'title': snippet.get('title', ''),
            'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'url': f"https://youtube.com/watch?v={video['id']}",
            'channel': snippet.get('channelTitle', ''),
            'views': int(stats.get('viewCount', 0)),
            'likes': int(stats.get('likeCount', 0)),
            'chef': chef_name
        }

    def run(self):
        print("\nWelcome to Recipe Tutorial Finder!")
        while True:
            recipe_name = input("\nEnter recipe name (or 'quit' to exit): ").strip()
            if recipe_name.lower() == 'quit':
                break
            cached = self.get_cached_results(recipe_name)
            results = cached if cached else self.search_videos(recipe_name)
            if results:
                self.cache_results(recipe_name, results)
                for idx, vid in enumerate(results, 1):
                    print(f"\n{idx}. {vid['title']} (Chef: {vid['chef']})")
                    print(f"   Channel: {vid['channel']}, Views: {vid['views']:,}, Likes: {vid['likes']:,}")
                    print(f"   URL: {vid['url']}")
            else:
                print("No results found.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        RecipeTutorialFinder().run()
    except Exception as e:
        logging.error(f"Application error: {e}")

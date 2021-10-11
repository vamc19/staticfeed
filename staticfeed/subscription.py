import hashlib
import json
import logging
import os.path
import time
from datetime import datetime, timezone
from typing import List

import feedparser
from feedparser import FeedParserDict

logger = logging.getLogger(__name__)


class SubscriptionException(Exception):
    pass


class Subscription:
    def __init__(self, url: str, cache_root: str, num_entries: int = 10) -> None:
        self.url = url.strip('/')
        self.num_entries = num_entries
        cache_root = os.path.abspath(cache_root)
        self.subscription_id = hashlib.sha256(self.url.encode('utf8')).hexdigest()

        self._cache_file_path = os.path.join(cache_root, self.subscription_id) + '.json'
        self._cache = self._read_cache()

        if 'feed_status' in self._cache:
            status = self._cache['feed_status']
            if status['code'] == 301:
                logger.debug(f'Using {status["url"]} instead of {self.url} since last run returned 304')
                self.url = status['url']
            if status['code'] == 410:
                logger.warning(f'{self.url} returned status 410 in a previous run. Feed will not be updated')

    def get_entries(self) -> List[dict]:
        return self._cache.get('entries', [])

    def get_title(self) -> str:
        return self._cache.get('title')

    def refresh(self):
        logger.debug(f'Refreshing {self.url}')
        etag: str = self._cache.get('feed_etag')
        last_modified: str = self._cache.get('feed_last_modified')

        feed = feedparser.parse(self.url, etag=etag, modified=last_modified)

        if feed.status == 301:  # permanent redirect, update url and continue
            logger.info(f'{self.url} is permanently redirected to {feed.href}')
            self._update_feed_status(feed)
        elif feed.status == 304:  # no changes since last update
            logger.debug(f'No changes to the feed {self.url} since last refresh')
            self._cache['last_refresh'] = datetime.now(timezone.utc).isoformat()
        elif feed.status == 410:  # gone
            logger.warning(f'Feed {self.url} no longer exists. It will not be updated anymore')
            self._update_feed_status(feed)

        if feed.status in [200, 301]:
            self._cache['title'] = feed.feed.title
            self._merge_feed_with_cache(feed.entries)
            self._cache['feed_etag'] = feed.get('etag')
            self._cache['feed_last_modified'] = feed.get('modified')

        self._save_cache_file()

    def _merge_feed_with_cache(self, fresh_entries: List[FeedParserDict]):
        entries = []
        def last_updated(e): return e.updated_parsed or e.published_parsed
        fresh_entries.sort(key=last_updated, reverse=True)
        cached_entries = self._cache.get('entries', [])

        inserted_entries = set()
        for entry in fresh_entries[:self.num_entries]:
            entries.append({
                'title': entry.title,
                'url': entry.link,
                'id': entry.id,
                'updated_on': time.strftime('%Y-%m-%dT%H:%M:%S', last_updated(entry)),
                # The following 2 should not be here. Code smell. Problem for another day
                'subscription_id': self.subscription_id,
                'subscription_title': self.get_title()
            })
            inserted_entries.add(entry.id)

        for cached_entry in cached_entries:
            if len(entries) >= self.num_entries:
                break
            if cached_entry['id'] not in inserted_entries:
                entries.append(cached_entry)

        self._cache['entries'] = entries

    def _update_feed_status(self, feed):
        self._cache['feed_status'] = {
            'code': feed.status,
            'url': feed.href,
            'updated_on': datetime.now(timezone.utc).isoformat()
        }

    def _save_cache_file(self):
        with open(self._cache_file_path, 'w') as cache_file:
            json.dump(self._cache, cache_file)

    def _read_cache(self) -> dict:
        cache = {}
        try:
            with open(self._cache_file_path, 'r') as cache_file:
                cache = json.load(cache_file)
        except OSError:
            logger.debug(f'Cannot find cache file for {self.url}. Proceeding with empty cache')
        except json.JSONDecodeError as err:
            logger.error(f'Error loading cache for {self.url}', self._cache_file_path, err)
            raise SubscriptionException('JSONDecodeError while loading cache file')

        return cache

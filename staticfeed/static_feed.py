import os.path
from datetime import datetime
from typing import List

import listparser

from .subscription import Subscription


class StaticFeed:
    def __init__(self, opml_path: str, cache_dir: str, output_dir: str, entries_per_feed: int = 10) -> None:
        self.opml_path = opml_path
        self.cache_dir = os.path.abspath(cache_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.entries_per_feed = entries_per_feed
        self.subscriptions: List[Subscription] = self._read_subscriptions()

        for folder in [self.cache_dir, self.output_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def _read_subscriptions(self) -> List[Subscription]:
        subscriptions = []
        opml = listparser.parse(self.opml_path)
        for feed in opml.feeds:
            subscription = Subscription(feed.url, self.cache_dir, self.entries_per_feed)
            subscriptions.append(subscription)

        return subscriptions

    def refresh(self):
        entries = []
        for subscription in self.subscriptions:
            subscription.refresh()
            entries.extend(subscription.get_posts())

        # easiest thing to do for now
        entries.sort(key=lambda e: datetime.fromisoformat(e['updated_time']), reverse=True)
        for i, e in enumerate(entries):
            print(f"{i + 1}. {e['updated_time']} - {e['title']}")
            print(f"==> {e['url']}")
            print(f"------------------------------------")

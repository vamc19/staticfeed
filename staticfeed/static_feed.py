import os.path
import tempfile
from datetime import datetime
from typing import List

import listparser
from jinja2 import Environment, FileSystemLoader

from .subscription import Subscription


class StaticFeed:
    def __init__(self, opml_path: str, cache_dir: str, output_dir: str, theme_dir: str,
                 entries_per_feed: int = 15, entries_per_page: int = 30) -> None:
        self.opml_path = opml_path
        self.cache_dir = os.path.abspath(cache_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.theme_dir = os.path.abspath(theme_dir)
        self.entries_per_feed = entries_per_feed
        self.entries_per_page = entries_per_page
        self.subscriptions: List[Subscription] = self._read_subscriptions()

        self._env = Environment(loader=FileSystemLoader(self.theme_dir))

        self.entries = []

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
        for subscription in self.subscriptions:
            subscription.refresh()
            self.entries.extend(subscription.get_entries())

        # easiest thing to do for now
        self.entries.sort(key=lambda e: datetime.fromisoformat(e['updated_time']), reverse=True)

    def generate_html(self):
        template = self._env.get_template('index.html')

        # Clean output dir. Assumes everything is a file for now.
        # This is dumb. Should Create a temp folder and replace output dir with it
        for path in os.listdir(self.output_dir):
            os.remove(os.path.join(self.output_dir, path))

        index_start = 0
        page_num = 1
        while index_start < len(self.entries):
            index_end = index_start + self.entries_per_page
            page_entries = self.entries[index_start:index_end]
            next_page = f'{page_num + 1}.html' if index_end < len(self.entries) else None

            html = template.render(entries=page_entries, next_page=next_page)
            file_name = 'index.html' if page_num == 1 else f'{page_num}.html'
            with open(os.path.join(self.output_dir, file_name), 'w') as page:
                page.write(html)

            index_start = index_end
            page_num += 1

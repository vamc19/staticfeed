import argparse
import logging
import os
import sys
from configparser import ConfigParser

from staticfeed import StaticFeed

DEFAULT_CACHE_DIR = os.path.join(os.getcwd(), 'cache')
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), 'output')
DEFAULT_CONFIG_PATH = os.path.join(os.getcwd(), 'config.ini')
DEFAULT_OPML_PATH = os.path.join(os.getcwd(), 'subscriptions.opml')
DEFAULT_THEME_PATH = os.path.join(os.getcwd(), 'theme/')

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    parser = argparse.ArgumentParser(prog='staticfeed', description='Web feed into a static website')
    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    parser.add_argument('--opml')
    parser.add_argument('--cache-dir')
    parser.add_argument('--output-dir')
    parser.add_argument('--theme-dir')

    config = {}
    args = parser.parse_args()
    if os.path.exists(args.config):
        config_parser = ConfigParser()
        config_parser.read(args.config)
        config = config_parser['StaticFeed']

    cache_dir = args.cache_dir or config.get('CacheDir', DEFAULT_CACHE_DIR)
    output_dir = args.output_dir or config.get('OutputDir', DEFAULT_OUTPUT_DIR)
    opml_path = args.opml or config.get('OpmlPath', DEFAULT_OPML_PATH)
    theme_dir = args.theme_dir or config.get('ThemeDir', DEFAULT_THEME_PATH)

    feeder = StaticFeed(opml_path, cache_dir, output_dir, theme_dir)
    feeder.refresh()
    feeder.generate_html()

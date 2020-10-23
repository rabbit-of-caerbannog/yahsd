import os
import sys
import time
import argparse
import itertools
import collections
import html.parser
import urllib.parse
import urllib.request


class HorribleSubsShow:
    BASE_URL = "https://horriblesubs.info/api.php"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0",
    }

    def __init__(self, showid: int):
        self.showid = showid

    def get(self, page: int = 0):
        timestamp = int(time.time() * 1000)
        params = [
            ("method", "getshows"),
            ("type", "show"),
            ("showid", self.showid),
            ("_", timestamp),
        ]
        if page != 0:
            params.append(("nextid", page),)

        query_string = urllib.parse.urlencode(params)

        url = self.BASE_URL + "?" + query_string
        req = urllib.request.Request(url, headers=self.HEADERS)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode()

        return html

    def get_first(self):
        yield self.get(page=0)

    def get_all(self):
        for page in itertools.count():
            html = self.get(page=page)
            if html == "DONE":
                break

            yield html


class EpisodeListParser(html.parser.HTMLParser):
    def __init__(self):
        self.episodes = {}
        self.show_name = None
        self.current_episode = None
        self.resolution = None
        self.data_count = 0

        super().__init__()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()

        if tag == "div" and "rls-info-container" in classes:
            self.current_episode = attrs["id"]
            self.episodes[self.current_episode] = {}
            return

        if tag == "div" and "rls-link" in classes:
            assert attrs["id"].startswith(self.current_episode)
            self.resolution = attrs["id"].split("-")[1]
            self.episodes[self.current_episode][self.resolution] = {}
            return

        if tag == "a" and attrs.get("title") == "Magnet Link":
            self.episodes[self.current_episode][self.resolution]["magnet"] = attrs[
                "href"
            ]
            return

        if tag == "a" and attrs.get("title") == "Torrent Link":
            self.episodes[self.current_episode][self.resolution]["torrent"] = attrs[
                "href"
            ]
            return

    def handle_endtag(self, tag):
        ...

    def handle_data(self, data):
        if self.data_count == 1:
            self.show_name = data.strip()

        self.data_count += 1


class ArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, description="Process some integers.", **kwargs)
        self.add_argument(
            "show_ids",
            metavar="ShowID(s)",
            type=int,
            nargs="+",
            help="HorribleSubs show id",
        )
        self.add_argument(
            "--all",
            dest="get",
            action="store_const",
            const=lambda show: show.get_all(),
            default=lambda show: show.get_first(),
            help="sum the integers (default: find the max)",
        )


class YahsDownloader:
    @classmethod
    def run(cls):
        args = ArgParser().parse_args()

        shows = collections.defaultdict(dict)
        for showid in args.show_ids:
            show = HorribleSubsShow(showid=showid)

            for body in args.get(show):
                parser = EpisodeListParser()
                parser.feed(body)
                shows[parser.show_name].update(parser.episodes)

        cls.output(shows)

    @classmethod
    def output(cls, shows: dict):
        for show in shows:
            for episode in shows[show]:
                for resolution in shows[show][episode]:
                    for medium, url in shows[show][episode][resolution].items():
                        sys.stdout.write(
                            cls.fmt(show, episode, resolution, medium, url)
                        )

    @staticmethod
    def fmt(show_name, episode, resolution, medium, url):
        def bold(string):
            start_bold = "\033[1m"
            end = "\033[0m"
            return f"{start_bold}{string}{end}"

        if sys.stdout.isatty() and os.getenv("NO_COLOR") is None:
            show_name = bold(show_name)
            episode = bold(episode)
            resolution = bold(resolution)

        return "\t".join([show_name, episode, medium, resolution, url]) + "\n"


if __name__ == "__main__":
    YahsDownloader.run()

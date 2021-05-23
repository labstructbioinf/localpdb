import json
import urllib
from abc import abstractmethod

import requests


class SearchStrategy:
    def __init__(self, url, queries):
        self.url = url
        self.queries = queries

    def _prepare_url(self, query):
        return self.url + 'json=' + urllib.parse.quote(json.dumps(query.build()), safe='')

    @abstractmethod
    def search(self):
        pass


class SyncSearch(SearchStrategy):
    def __init__(self, url, queries):
        super().__init__(url, queries)

    def search(self):
        responses = []
        with requests.Session() as session:
            for query in self.queries:
                response = session.get(self._prepare_url(query))
                responses.append(query.parse_response(response))
        return responses


class Searcher:
    def __init__(self, url, queries):
        self.queries = queries
        self.search_strategy = None
        self.set_strategy(url, queries)

    def set_strategy(self, url, queries):
        self.search_strategy = SyncSearch(url, queries)

    def perform_search(self):
        return self.search_strategy.search()

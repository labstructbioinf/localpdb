import requests
import pandas as pd
import json


class ServiceUtils:
    def __init__(self, search_attrs, service):
        self.search_attrs = search_attrs
        self.service = service

    def to_dict(self):
        return {"parameters": {attr: getattr(self.service, attr) for attr in self.search_attrs}}


class SeqmotifService:

    def __init__(self, value, pattern_type, target="pdb_protein_sequence"):
        self.value = value
        self.pattern_type = pattern_type
        self.target = target
        self.name = 'seqmotif'
        self.search_attrs = ['value', 'pattern_type', 'target']
        self.service_util = ServiceUtils(self.search_attrs, self)

    def parse_response(self, response):
        if response.status_code == 200:
            return None
        return pd.DataFrame(response.json()['result_set'])


class TerminalQuery:
    def __init__(self, service, return_type):
        self.service = service
        self.return_type = return_type
        self.__type = "terminal"

    def build(self):
        query_dict = {"type": self.__type, "service": self.service.name}
        query_dict = {**query_dict, **self.service.service_util.to_dict()}
        return {"query": query_dict, "return_type": self.return_type}


class SyncSearch:
    def __init__(self, url, queries):
        self.url = url
        self.queries = queries

    def search(self):
        responses = []
        with requests.Session() as session:
            for query in self.queries:
                response = session.get(self.url, json=query.build())
                responses.append(query.service.parse_response(response))
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


w = Searcher("https://search.rcsb.org/rcsbsearch/v1/query?",
             [TerminalQuery(
                 SeqmotifService("CA", 'prosite', "pdb_protein_sequence"),
                 "polymer_entity")])
print(w.perform_search())

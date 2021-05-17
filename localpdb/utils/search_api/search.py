import json
import urllib
from abc import abstractmethod

import requests
from queries import TerminalQuery
from services import SeqmotifService, SequenceService, StructureService, StructMotifService


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


class SearchMotifCommand:
    def __init__(self, query, type_='prosite'):
        self.success = 1
        self.query = query
        self.type_ = type_

    def execute(self):
        searcher = Searcher("https://search.rcsb.org/rcsbsearch/v1/query?",
                            [TerminalQuery(
                                SeqmotifService(self.query, self.type_, "pdb_protein_sequence"), "entry")])
        resp = searcher.perform_search()
        if resp[0] is None:
            return None
        return resp[0]


class SequenceSimilarityCommand:
    def __init__(self, sequence, evalue=1, identity=0.9):
        self.success = 1
        self.sequence = sequence
        self.evalue = evalue
        self.identity = identity

    def execute(self):
        searcher = Searcher("https://search.rcsb.org/rcsbsearch/v1/query?",
                            [TerminalQuery(
                                SequenceService(self.sequence, self.evalue, self.identity, "pdb_protein_sequence"), "entry")])
        resp = searcher.perform_search()
        if resp[0] is None:
            return None
        return resp[0]


class StructureSimilarityCommand:
    def __init__(self, entry_id, assembly_id=1, operator = "strict_shape_match"):
        self.success = 1
        self.entry_id = entry_id
        self.assembly_id = assembly_id
        self.operator = operator

    def execute(self):
        searcher = Searcher("https://search.rcsb.org/rcsbsearch/v1/query?",
                            [TerminalQuery(
                                StructureService(self.entry_id, self.assembly_id, self.operator), "entry")])
        resp = searcher.perform_search()
        if resp[0] is None:
            return None
        return resp[0]


class StructureMotifCommand:
    def __init__(self, entry_id, residue_ids, score_cutoff=0, exchanges=None):
        self.success = 1
        self.entry_id = entry_id
        self.residue_ids = residue_ids
        self.score_cutoff= score_cutoff
        self.exchanges = exchanges or {}

    def execute(self):
        searcher = Searcher("https://search.rcsb.org/rcsbsearch/v1/query?",
                            [TerminalQuery(
                                StructMotifService(self.entry_id, self.residue_ids, self.score_cutoff, self.exchanges), "assembly")])
        resp = searcher.perform_search()
        if resp[0] is None:
            return None
        return resp[0]

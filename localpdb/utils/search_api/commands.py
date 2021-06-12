from .queries import TerminalQuery, QueryParams
from .search import Searcher
from .services import SeqmotifService, SequenceService, StructureService, StructMotifService, TextService


class Command:
    def __init__(self, url="https://search.rcsb.org/rcsbsearch/v1/query?", resp_type="entry",
                 start=0, rows=100):
        self._set_source(url, resp_type)
        self._set_resp_limits(start, rows)

    def _set_source(self, url, resp_type):
        self.url = url
        if resp_type not in QueryParams.RETURN_TYPES.value:
            raise NameError('Unknown return type, available {}'.format(QueryParams.RETURN_TYPES.value))
        self.resp_type = resp_type

    def _set_resp_limits(self, start, rows):
        self.start = start
        self.rows = rows

    @classmethod
    def set_source(cls, url, resp_type):
        cls.url = url
        if resp_type not in QueryParams.RETURN_TYPES.value:
            raise NameError('Unknown return type, available {}'.format(QueryParams.RETURN_TYPES.value))
        cls.resp_type = resp_type

    @classmethod
    def set_parser(cls, parser):
        cls.parser = parser

    def execute(self):
        pass


class SearchMotifCommand(Command):
    def __init__(self, query, type_='prosite', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success = 1
        self.query = query
        self.type_ = type_

    def execute(self):
        searcher = Searcher(self.url,
                            [TerminalQuery(
                                SeqmotifService(self.query, self.type_, "pdb_protein_sequence"), self.resp_type,
                                start=self.start, rows=self.rows, response_parser=self.parser)])
        resp = searcher.perform_search()
        return resp[0]


class SequenceSimilarityCommand(Command):
    def __init__(self, sequence, evalue=1, identity=0.9, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success = 1
        self.sequence = sequence
        self.evalue = evalue
        self.identity = identity

    def execute(self):
        searcher = Searcher(self.url,
                            [TerminalQuery(
                                SequenceService(self.sequence, self.evalue, self.identity, "pdb_protein_sequence"),
                                self.resp_type, start=self.start, rows=self.rows, response_parser=self.parser)])
        resp = searcher.perform_search()
        return resp[0]


class StructureSimilarityCommand(Command):
    def __init__(self, entry_id, assembly_id=1, operator="strict_shape_match", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success = 1
        self.entry_id = entry_id
        self.assembly_id = assembly_id
        self.operator = operator

    def execute(self):
        searcher = Searcher(self.url,
                            [TerminalQuery(
                                StructureService(self.entry_id, self.assembly_id, self.operator), self.resp_type,
                                start=self.start, rows=self.rows, response_parser=self.parser)])
        resp = searcher.perform_search()
        return resp[0]


class StructureMotifCommand(Command):
    def __init__(self, entry_id, residue_ids, score_cutoff=0, exchanges=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success = 1
        self.entry_id = entry_id
        self.residue_ids = residue_ids
        self.score_cutoff = score_cutoff
        self.exchanges = exchanges or {}

    def execute(self):
        searcher = Searcher(self.url,
                            [TerminalQuery(
                                StructMotifService(self.entry_id, self.residue_ids, self.score_cutoff, self.exchanges),
                                self.resp_type, start=self.start, rows=self.rows, response_parser=self.parser)])
        resp = searcher.perform_search()
        return resp[0]


class TextCommand(Command):
    def __init__(self, attribute, operator, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attribute = attribute
        self.operator = operator
        self.value = value

    def execute(self):
        searcher = Searcher(self.url,
                            [TerminalQuery(
                                TextService(self.attribute, self.operator, self.value),
                                self.resp_type, start=self.start, rows=self.rows, response_parser=self.parser)])
        resp = searcher.perform_search()
        return resp[0]

    @staticmethod
    def get_doc():
        TextService.set_input_params()
        return TextService.input_params

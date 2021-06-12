from .tools.text_api_input_fetcher import read_text_api_input


class ServiceUtils:
    def __init__(self, search_attrs, service):
        self.search_attrs = search_attrs
        self.service = service

    def to_dict(self):
        empty_allowed = self.service.empty_allowed if  hasattr(self.service, 'empty_allowed') else {}
        return {"parameters": {attr: getattr(self.service, attr) for attr in self.search_attrs
                               if getattr(self.service, attr) or attr in empty_allowed}}


class SeqmotifService:

    def __init__(self, value, pattern_type, target="pdb_protein_sequence"):
        self.value = value
        self.pattern_type = pattern_type
        self.target = target
        self.name = 'seqmotif'
        self.search_attrs = ['value', 'pattern_type', 'target']
        self.service_util = ServiceUtils(self.search_attrs, self)


class SequenceService:
    def __init__(self, value, evalue_cutoff=1, identity_cutoff=0.9, target="pdb_protein_sequence"):
        self.value = value
        self.evalue_cutoff = evalue_cutoff
        self.identity_cutoff = identity_cutoff
        self.target = target
        self.name = 'sequence'
        self.search_attrs = ['value', 'identity_cutoff', 'evalue_cutoff', 'target']
        self.service_util = ServiceUtils(self.search_attrs, self)


class StructureService:
    def __init__(self, entry_id, assembly_id=1, operator='strict_shape_match'):
        self.value = {'entry_id': entry_id, 'assembly_id': str(assembly_id)}
        self.operator = operator
        self.name = 'structure'
        self.search_attrs = ['value', 'operator']
        self.service_util = ServiceUtils(self.search_attrs, self)


class StructMotifService:
    def __init__(self, entry_id, residue_ids, score_cutoff=0, exchanges=None):
        self.value = {'data': entry_id, 'residue_ids': residue_ids}
        self.exchanges = exchanges or []
        self.score_cutoff = score_cutoff
        self.name = 'strucmotif'
        self.search_attrs = ['value', 'exchanges', 'score_cutoff']
        self.empty_allowed = ['exchanges']
        self.service_util = ServiceUtils(self.search_attrs, self)


class TextService:
    input_params = None

    def __init__(self, attribute, operator, value):
        self.attribute = attribute
        self.operator = operator
        self.value = value
        self.name = 'text'
        self.search_attrs = ['attribute', 'operator', 'value']
        self.service_util = ServiceUtils(self.search_attrs, self)
        self.__input_params = None

    @classmethod
    def set_input_params(cls, source='https://search.rcsb.org/rcsbsearch/v1/metadata/schema'):
        if cls.input_params is None:
            cls.input_params = read_text_api_input(source,)

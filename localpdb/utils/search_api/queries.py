from enum import Enum


class QueryParams(Enum):
    RETURN_TYPES = ('entry', 'assembly', 'polymer_entity', 'non_polymer_entity', 'polymer_instance')


class TerminalQuery:
    def __init__(self, service, return_type, start=0, rows=1000, response_parser=None):
        self.service = service
        self.return_type = return_type
        self.__type = "terminal"
        self.response_status = None
        self.start = start
        self.rows = rows
        self.request_options = RequestOption()
        self._add_request_options()
        self.response_parser = response_parser

    def _add_request_options(self):
        self.request_options.add_pager(self.start, self.rows)

    def build(self):
        query_dict = {"type": self.__type, "service": self.service.name}

        query_dict = {**query_dict, **self.service.service_util.to_dict()}
        return {"query": query_dict, "return_type": self.return_type,
                "request_options": self.request_options.options}

    def parse_response(self, response):
        self.response_status = response.status_code
        if response.status_code != 200:
            return None if not self.response_parser else self.response_parser.parse_wrong(response)
        return response.json() if not self.response_parser else self.response_parser.parse(response)


class RequestOption:
    def __init__(self):
        self.options = {}

    def add_pager(self, start=0, rows=1000):
        if rows == -1:
            self.options.update({"return_all_hits": True})
        else:
            self.options.update({'pager': {'start': start, 'rows': rows}})

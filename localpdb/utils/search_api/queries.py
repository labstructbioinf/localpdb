import pandas as pd


class TerminalQuery:
    def __init__(self, service, return_type):
        self.service = service
        self.return_type = return_type
        self.__type = "terminal"
        self.response_status = None

    def build(self):
        query_dict = {"type": self.__type, "service": self.service.name}

        query_dict = {**query_dict, **self.service.service_util.to_dict()}
        return {"query": query_dict, "return_type": self.return_type}

    def parse_response(self, response):
        self.response_status = response.status_code
        if response.status_code != 200:
            return None
        response = response.json()['result_set']
        resp_dict = {'identifier': [], 'score': [], 'service_type': [], 'node_id': [], 'orginal_score': [],
                     'norm_score': [], 'match_context': []}
        for result in response:
            for service in result['services']:
                for node in service['nodes']:
                    resp_dict['identifier'].append(result['identifier'])
                    resp_dict['score'].append(result['score'])
                    resp_dict['service_type'].append(service['service_type'])
                    resp_dict['node_id'].append(node['node_id'])
                    resp_dict['orginal_score'].append(node['original_score'])
                    resp_dict['norm_score'].append(node['norm_score'])
                    resp_dict['match_context'].append(node.get('match_context'))

        resp_dict = pd.DataFrame(resp_dict)
        resp_dict.set_index(['identifier', 'service_type', 'node_id'], inplace=True)
        return resp_dict

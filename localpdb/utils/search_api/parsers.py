import pandas as pd


class ResponseParser:
    def __init__(self, raw=False):
        self.raw = raw

    def parse(self, response):
        response = response.json()
        for id_ in response['result_set']:
            if '.' in id_['identifier']:
                pdbid, chain = id_['identifier'].split('.')
                id_['identifier'] = f'{pdbid.lower()}_{chain.upper()}'
            else:
                id_['identifier'] = id_['identifier'].lower()
        if self.raw:
            response = response['result_set']
            return pd.DataFrame(response)
        else:
            response = response['result_set']
            resp_dict = {'identifier': [], 'score': [], 'orginal_score': [],
                         'norm_score': [], 'match_context': []}
            for result in response:
                for service in result['services']:
                    for node in service['nodes']:
                        resp_dict['identifier'].append(result['identifier'])
                        resp_dict['score'].append(result['score'])
                        resp_dict['orginal_score'].append(node['original_score'])
                        resp_dict['norm_score'].append(node['norm_score'])
                        resp_dict['match_context'].append(node.get('match_context'))
            resp_dict = pd.DataFrame(resp_dict)
            resp_dict.set_index(['identifier'], inplace=True)
            return resp_dict

    def parse_wrong(self, response):
        try:
            return pd.DataFrame(response.json())
        except Exception:
            return "Could not find response. Please revise your query."

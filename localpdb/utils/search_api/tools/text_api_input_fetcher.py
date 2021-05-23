import pandas as pd
import requests


def read_netesd(dict_, storage, key=''):
    if dict_['type'] == 'object':
        for prop in dict_['properties']:
            read_netesd(dict_['properties'][prop], storage, key + '.' + prop)
    elif dict_['type'] == 'array':

        if dict_['items'].get('properties'):
            for item in dict_['items']['properties']:
                read_netesd(dict_['items']['properties'][item], storage, key + '.' + item)

    else:
        storage.append((key[1:], dict_['type'], dict_.get('description')))


def read_text_api_input(source):
    props = []
    data = requests.get(source).json()
    read_netesd(data, props)
    data = pd.DataFrame(props, columns=['attribute', 'type', 'description'])
    data = data.set_index('attribute')
    return data

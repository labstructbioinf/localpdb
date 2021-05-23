from .config import load_remote_source
from .search_api.commands import StructureMotifCommand, SearchMotifCommand, SequenceSimilarityCommand, \
    StructureSimilarityCommand, TextCommand

from .search_api.parsers import ResponseParser


class CommandFactory:
    def __init__(self, raw_response=False):
        self.config = load_remote_source()
        self.commands = {'strucmotif': StructureMotifCommand,
                         'sequence': SequenceSimilarityCommand,
                         'structure': StructureSimilarityCommand,
                         'seqmotif': SearchMotifCommand,
                         'text': TextCommand}
        for command_name, command in self.commands.items():
            command.set_source('/'.join([self.config['api']['url'],
                                         self.config['api']['version'],
                                         self.config['api']['query']]),
                               self.config['api']['return_type'])
            command.set_parser(ResponseParser(raw_response))

    def get(self, name):
        return self.commands[name]

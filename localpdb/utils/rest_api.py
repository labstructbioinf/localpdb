from .config import load_remote_source
from .search_api.commands import StructureMotifCommand, SearchMotifCommand, SequenceSimilarityCommand, \
    StructureSimilarityCommand


class CommandFactory:
    def __init__(self):
        self.config = load_remote_source()
        self.commands = {'strucmotif': StructureMotifCommand,
                         'sequence': SequenceSimilarityCommand,
                         'structure': StructureSimilarityCommand,
                         'seqmotif': SearchMotifCommand}
        for command_name, command in self.commands.items():
            command.set_source('/'.join([self.config['api']['url'],
                                         self.config['api']['version'],
                                         self.config['api']['query']]),
                               self.config['api']['return_type'])

    def get(self, name):
        return self.commands[name]

from localpdb.utils.rest_api import CommandFactory

SEQMOTIF = 'seqmotif'
STRUCMOTIF = 'strucmotif'
SEQUENCE = 'sequence'
STRUCTURE = 'structure'
TEXT = 'text'

EXPECTED_RESPONSE_LENGTH = {SEQMOTIF: 505,
                            STRUCMOTIF: 991,
                            SEQUENCE: 1009,
                            STRUCTURE: 18,
                            TEXT: 216}

INPUT_PARAMS = {SEQMOTIF: ['C-x(2,4)-C-x(3)-[LIVMFYWC]-x(8)-H-x(3,5)-H.'],
                SEQUENCE: [
                    'MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLPARTVETRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMNCKCVIS'],
                STRUCTURE: ['1CLL'],
                STRUCMOTIF: ["2mnr", [
                    {
                        "label_asym_id": "A",
                        "label_seq_id": 162
                    },
                    {
                        "label_asym_id": "A",
                        "label_seq_id": 193
                    },
                    {
                        "label_asym_id": "A",
                        "label_seq_id": 219
                    },
                    {
                        "label_asym_id": "A",
                        "label_seq_id": 245
                    }]],
                TEXT: ['', '', 'hamp']}


def is_length_match(expected, current, tolerance=0.9):
    return abs(current - expected) / expected <= (1 - tolerance)


class TestCommands:
    factory = CommandFactory(raw_response=True)

    def test_search_motif_command(self):
        command = self.factory.get(SEQMOTIF)(*INPUT_PARAMS[SEQMOTIF], rows=-1)
        data = command.execute()
        assert is_length_match(EXPECTED_RESPONSE_LENGTH[SEQMOTIF], len(data))

    def test_sequence_similarity(self):
        command = self.factory.get(SEQUENCE)(*INPUT_PARAMS[SEQUENCE], rows=-1, identity=0.1)
        data = command.execute()
        assert is_length_match(EXPECTED_RESPONSE_LENGTH[SEQUENCE], len(data))

    def test_structure_similarity(self):
        command = self.factory.get(STRUCTURE)(*INPUT_PARAMS[STRUCTURE], rows=-1)
        data = command.execute()
        assert is_length_match(EXPECTED_RESPONSE_LENGTH[STRUCTURE], len(data))

    def test_structure_motif(self):
        command = self.factory.get(STRUCMOTIF)(*INPUT_PARAMS[STRUCMOTIF], rows=-1)
        data = command.execute()
        assert is_length_match(EXPECTED_RESPONSE_LENGTH[STRUCMOTIF], len(data))

    def test_text_search(self):
        command = self.factory.get(TEXT)(*INPUT_PARAMS[TEXT], rows=-1)
        data = command.execute()
        assert is_length_match(EXPECTED_RESPONSE_LENGTH[TEXT], len(data))

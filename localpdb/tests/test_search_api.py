from localpdb.utils.rest_api import CommandFactory

SEQMOTIF = 'seqmotif'
STRUCMOTIF = 'strucmotif'

EXPECTED_RESPONSE_LENGTH = {SEQMOTIF: 2151,
                            'strucmotif': 1}

INPUT_PARAMS = {SEQMOTIF: ['AA'],
                STRUCMOTIF}


def is_length_match(expected, current, tolerance=0.9):
    return abs(current - expected) / expected <= (1 - tolerance)


class TestCommands:
    factory = CommandFactory(raw_response=True)

    def test_search_motif_command(self):
        command = self.factory.get(SEQMOTIF)(*INPUT_PARAMS[SEQMOTIF], rows=-1)
        data = command.execute()
        assert is_length_match(EXPECTED_RESPONSE_LENGTH[SEQMOTIF], len(data))

    def
""" 
Module: audit_tie_breaker
Author: Berj K. Chilingirian
Date:   10 August 2016

Description:

    The Australian Senate Election (ASE) may require an Australian Election 
    Official (AEO) to break a tie. There are three cases in which ties must
    be broken manually by an AEO:

        Case 1: Election Order Tie

            If multiple candidates hold the same number of votes and that 
            number is greater than the quota, then a previous round in which
            those candidates held a differing number of votes is used to
            determine the election order. If no such round exists, the AEO 
            determines a permutation of candidate IDs, specifying the order 
            in which those candidates are elected.

        Case 2: Election Tie

            If there are two final continuing candidates, with one remaining 
            vacancy, and both candidates hold the same number of votes, the 
            AEO decides which candidate is elected.

        Case 3: Exclusion Tie

            If a candidate must be excluded, then the lowest number of votes
            held by any candidate is found. If multiple candidates hold that
            number of votes, the same tie breaker system as in (1) is used.
            If that fails, the AEO decides what candidate is excluded.

    We want our auditing procedures to be as consistent as possible with the
    real ASE. However, the Commonwealth Electoral Act of 1981 does not specify 
    the tie-breaking procedure of an AEO. Thus, we use tie-breaking information
    from the real election to resolve ties encountered during our audit.

    To do this, we:

        (1) Ingest tie-breaking information from the real ASE.

        (2) Construct a directed, acyclic graph where a directed edge from A to B 
            represents situations where A is elected over B (cases 1, 2) or B is 
            excluded (case 3). Note that more than one edge may be created by a 
            given tie-breaking event.

        (3) Sort the vertices into a linear order using a random topological sort.

        (4) Use the linear ordering discovered in Step 3 to break all ties
            encountered during the audit. In other words, given candidate IDs A
            and B, prefer electing/not-excluding the candidate earlier in the
            linear order.

Usage:

    .. code-block:: python3

        >>> import audit_tie_breaker
        >>> atb = AuditTieBreaker(['A', 'B', 'C', 'D', 'E', 'F', 'G'], verbose=True)
        >>> atb.load_election(
                [   # Election Order Tie Events
                    [
                        [
                            ['A', 'B', 'C'],
                            ['A', 'C', 'B'],
                            ['B', 'A', 'C'],
                            ['B', 'C', 'A'],
                            ['C', 'A', 'B'],
                            ['C', 'B', 'A'],
                        ],
                        ['B', 'A', 'C'],
                    ],
                ],
                [   # Election Tie Events
                    [
                        ['D', 'G'],
                        'G',
                    ],
                ],
                [   # Exclusion Tie Events
                    [
                        ['D', 'E', 'F'],
                        'E',
                    ],
                ],
            )
        = Building Audit Tie-Breaking Graph...
         - Added edge B -> C because B preferred to C in resolution for election order tie.
         - Added edge B -> A because B preferred to A in resolution for election order tie.
         - Added edge C -> A because C preferred to A in resolution for election order tie.
         - Added edge G -> D because G elected over D.
         - Added edge D -> E because E excluded over D.
         - Added edge F -> E because E excluded over F.
         --> Linear order determined as B, C, A, F, G, D, E.

        = Verifying linear order is consisent with real election's tie-breaking events...
         - Election order tie between ['A', 'B', 'C'] broken with permutation ['B', 'C', 'A'].
         - Election tie between ['D', 'G'] broken by electing G.
         - Exclusion tie between ['D', 'E', 'F'] broken by excluding E.
         --> Linear order is consistent with real election's tie-breaking events.

        >>> atb.break_tie(['A', 'B', 'C'], 1)
         - Election order tie between ['A', 'B', 'C'] broken with permutation ['B', 'C', 'A'].
"""

import itertools
import random
import sys


class AuditTieBreaker(object):
    """ Implements a class for breaking ties encountered during an audit.

    :ivar _vertices: A mapping from a vertex in the audit tie breaking graph to its
        neighbors.
    :vartype _vertices: dict
    :ivar _print_fn: A function which takes a string as input and writes it to the
        appropriate file.
    :vartype _print_fn: function
    :ivar _linear_order: A linear ordering of the candidate IDs of all candidates in
        the contest being audited. The linear ordering is represented as a mapping
        from a candidate ID to its position in the linear order.
    :vartype _linear_order: dict
    """
    WRITE_OPT = 'w'

    COMMA_DELIM = ', '

    # Tie-Breaking Event IDs.
    ELECTION_ORDER_TIE_ID = 1
    ELECTION_TIE_ID = 2
    EXCLUSION_TIE_ID = 3

    # Messages to be printed during verbose mode.
    BUILDING_GRAPH_MSG = '= Building Audit Tie-Breaking Graph...'
    VERIFY_LINEAR_ORDER_MSG = '\n= Verifying linear order is consisent with real election\'s tie-breaking events...'
    IS_CONSISTENT_MSG = ' --> Linear order is consistent with real election\'s tie-breaking events.\n'

    # Messages to be printed during verbose mode - require formatting.
    ADDED_ELECTION_ORDER_TIE_EDGE = ' - Added edge {0} -> {1} because {0} preferred to {1} in resolution for election order tie.'
    ADDED_ELECTION_TIE_EDGE = ' - Added edge {0} -> {1} because {0} elected over {1}.'
    ADDED_EXCLUSION_TIE_EDGE = ' - Added edge {0} -> {1} because {1} excluded over {0}.'
    LINEAR_ORDER_MSG = ' --> Linear order determined as {0}.'
    ELECTION_ORDER_TIE_BREAK = ' - Election order tie between {0} broken with permutation {1}.'
    ELECTION_TIE_BREAK = ' - Election tie between {0} broken by electing {1}.'
    EXCLUSION_TIE_BREAK = ' - Exclusion tie between {0} broken by excluding {1}.'

    def __init__(self, candidate_ids, seed=1, verbose=False, out_f=None):
        """ Initializes the `AuditTieBreaker` object.

        :param candidate_ids: A list of the candidate IDs of all candidates in the
            election contest.
        :type candidate_ids: list
        :param verbose: A flag indicating whether or not the `AuditTieBreaker`
            object should be verbose when loading data/breaking ties.
        :type verbose: bool
        :param seed: An integer specifying the random seed to use when determining
            the random topological sort of the candidate IDs of all candidates in
            the election (default: 1).
        :type seed: int
        :param out_f: A string representing the name of a file to write all debug
            information to (default: stdout). Only used when `verbose` is true.
        :type out_f: str
        """
        random.seed(seed)
        self._vertices = {candidate_id : [] for candidate_id in candidate_ids}
        self._print_fn = AuditTieBreaker._setup_print_fn(out_f) if verbose else lambda x : None
        self._linear_order = {}

    @staticmethod
    def _setup_print_fn(out_f):
        """ Returns a function to be used for writing verbose information.

        :param out_f: A string representing the name of a file to write all debug
            information to.
        :type out_f: str

        :return: A function which takes a string as input and writes it to the
            appropriate file.
        :rtype: function
        """
        if out_f is not None:
            sys.stdout = open(out_f, AuditTieBreaker.WRITE_OPT)
        return lambda x : print(x)

    def _visit(self, v, linear_order):
        """ Explores the neighbors of the given node recursively and then adds the
        explored node to the head of the linear order.

        :param v: A candidate ID.
        :type v: int
        :param linear_order: The linear order of candidate IDs so far.
        :type linear_order: list
        """
        if v in linear_order:
            # Do not explore a node twice.
            return
        random.shuffle(self._vertices[v])
        for u in self._vertices[v]:
            self._visit(u, linear_order)
        linear_order.insert(0, v)

    def load_events(self, election_order_ties, election_ties, exclusion_ties):
        """ Loads all tie-breaking events specified in `events_f`.

        :param election_order_ties: A list of 2-tuples representing election order
            tie events where the first entry is the permutations of election orders
            and the second entry is the permutation that resovled the tie.
        :type election_order_ties: list
        :param election_ties: A list of 2-tuples representing election tie events
            where the first entry is the IDs of the candidates tied for election
            and the second entry is the candidate ID that resovled the tie.
        :type election_ties: list
        :param exclusion_ties: A list of 2-tuples representing exclusion tie events
            where the first entry is the IDs of the candidates tied for exclusion
            and the second entry is the candidate ID that resovled the tie.
        :type exclusion_ties: list
        """
        # Construct audit tie-breaking graph.
        self._print_fn(AuditTieBreaker.BUILDING_GRAPH_MSG)

        # Process Election Order Tie Events.
        for _, resolution in election_order_ties:
            for src_cid, dest_cid in itertools.combinations(resolution, 2):
                self._vertices[src_cid].append(dest_cid)
                self._print_fn(AuditTieBreaker.ADDED_ELECTION_ORDER_TIE_EDGE.format(
                    src_cid,
                    dest_cid,
                ))

        # Process Election Tie Events.
        for candidate_ids, resolution in election_ties:
            for cid in candidate_ids:
                if cid != resolution:
                    self._vertices[resolution].append(cid)
                    self._print_fn(AuditTieBreaker.ADDED_ELECTION_TIE_EDGE.format(
                        resolution,
                        cid,
                    ))

        # Process Exclusion Tie Events.
        for candidate_ids, resolution in exclusion_ties:
            for cid in candidate_ids:
                if cid != resolution:
                    self._vertices[cid].append(resolution)
                    self._print_fn(AuditTieBreaker.ADDED_EXCLUSION_TIE_EDGE.format(
                        cid,
                        resolution,
                    ))

        # Determine a random topological sorting of the vertices in the audit tie-breaking graph.
        vertices = sorted(self._vertices.keys())
        random.shuffle(vertices)
        linear_order = []
        for v in vertices:
            self._visit(v, linear_order)
        self._linear_order = {linear_order[i] : i for i in range(len(linear_order))}
        self._print_fn(AuditTieBreaker.LINEAR_ORDER_MSG.format(
            AuditTieBreaker.COMMA_DELIM.join([str(x) for x in linear_order]))
        )

        # Verify linear order is consistent with the real election's tie-breakin events.
        self._print_fn(AuditTieBreaker.VERIFY_LINEAR_ORDER_MSG)
        for permutations, resolution in election_order_ties:
            assert self.break_election_order_tie(permutations) == permutations.index(resolution)
        for candidate_ids, resolution in election_ties:
            assert self.break_election_tie(candidate_ids) == candidate_ids.index(resolution)
        for candidate_ids, resolution in exclusion_ties:
            assert self.break_exclusion_tie(candidate_ids) == candidate_ids.index(resolution)
        self._print_fn(AuditTieBreaker.IS_CONSISTENT_MSG)

    def break_tie(self, candidate_ids, case_num):
        """ Returns the resolution for the given candidate IDs and case number.

        :param candidate_ids: A list of candidate IDs.
        :type candidate_ids: list
        :param case_num: A integer identifying the tie-breaking case.
        :type case_num: int

        :return: The resolution for the given candidate IDs and case number.
        :rtype: A single candidate ID (cases 2,3) or a permutation of the given cadndidate IDs
            (case 1).
        """
        cids_to_order = {cid : self._linear_order[cid] for cid in candidate_ids}
        resolution = sorted(cids_to_order, key=cids_to_order.__getitem__)

        if case_num == AuditTieBreaker.ELECTION_ORDER_TIE_ID:
            result = resolution
            self._print_fn(AuditTieBreaker.ELECTION_ORDER_TIE_BREAK.format(candidate_ids, result))
        elif case_num == AuditTieBreaker.ELECTION_TIE_ID:
            result = resolution[0]
            self._print_fn(AuditTieBreaker.ELECTION_TIE_BREAK.format(candidate_ids, result))
        else:
            result = resolution[-1]
            self._print_fn(AuditTieBreaker.EXCLUSION_TIE_BREAK.format(candidate_ids, result))
        return result

    def break_election_order_tie(self, permutations):
        """ Convenience wrapper for breaking election order ties. """
        return permutations.index(tuple(self.break_tie(permutations[0], AuditTieBreaker.ELECTION_ORDER_TIE_ID)))

    def break_election_tie(self, candidate_ids):
        """ Convenience wrapper for breaking election ties. """
        return candidate_ids.index(self.break_tie(candidate_ids, AuditTieBreaker.ELECTION_TIE_ID))

    def break_exclusion_tie(self, candidate_ids):
        """ Convenience wrapper for breaking exclusion ties. """
        return candidate_ids.index(self.break_tie(candidate_ids, AuditTieBreaker.EXCLUSION_TIE_ID))


def test_audit_tie_breaker():
    """ Tests the `AuditTieBreaker` implementation. """
    # Test `AuditTieBreaker` implementation.
    audit_tb = AuditTieBreaker(['A', 'B', 'C', 'D', 'E', 'F', 'G'], verbose=True)
    audit_tb.load_events(
        [   # Election Order Tie Events
            [
                [
                    ['A', 'B', 'C'],
                    ['A', 'C', 'B'],
                    ['B', 'A', 'C'],
                    ['B', 'C', 'A'],
                    ['C', 'A', 'B'],
                    ['C', 'B', 'A'],
                ],
                ['B', 'A', 'C'],
            ],
        ],
        [   # Election Tie Events
            [
                ['D', 'G'],
                'G',
            ],
        ],
        [   # Exclusion Tie Events
            [
                ['D', 'E', 'F'],
                'E',
            ],
        ],
    )
    audit_tb._print_fn('= Running AuditTieBreaker tests...')
    assert audit_tb.break_tie(['A', 'B', 'C'], 1) == ['B', 'A', 'C']
    assert audit_tb.break_tie(['D', 'E', 'F'], 3) == 'E'
    assert audit_tb.break_tie(['D', 'G'], 2) == 'G'
    assert audit_tb.break_tie(['B', 'F'], 2) == 'B'  # Test depends on random.seed of 1.
    assert audit_tb.break_tie(['B', 'F'], 3) == 'F'  # Test depends on random.seed of 1.
    audit_tb._print_fn(' --> Tests PASSED!')


if __name__ == '__main__':
    # Runs AuditTieBreaker Tests.
    test_audit_tie_breaker()

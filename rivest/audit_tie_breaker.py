""" 
Module: audit_tie_breaker
Author: Berj K. Chilingirian
Date:   7 August 2016

Description:

    The Australian Senate Election (ASE) may require an Australian Election 
    Official (AEO) to break a tie. There are three cases in which ties must
    be broken manually by an AEO:

        Case 1:

            If multiple candidates hold the same number of votes and that 
            number is greater than the quota, then a previous round in which
            those candidates held a differing number of votes is used to
            determine the election order. If no such round exists, the AEO 
            determines a permutation of candidate IDs, specifying the order 
            in which those candidates are elected.

        Case 2:

            If there are two final continuing candidates, with one remaining 
            vacancy, and both candidates hold the same number of votes, the 
            AEO decides which candidate is elected.

        Case 3:

            If a candidate must be excluded, then the lowest number of votes
            held by any candidate is found. If multiple candidates hold that
            number of votes, the same tie breaker system in (1) is used. If 
            that fails, the AEO decides what candidate is excluded.

    We want our auditing procedures to be as consistent as possible with the
    real ASE. However, the Commonwealth Electoral Act of 1981 does not specify 
    the tie-breaking procedure of an AEO. Thus, we use tie-breaking information
    from the real election to resolve ties encountered during our audit.

    To do this, we:

        (1) Ingest tie-breaking information (JSON) from the real ASE.

            .. code-block:: json

                {
                    'events': [
                       (17, ['A', 'B', 'C'], 'B', 2),
                       (21, ['D', 'E', 'F'], ['E', 'F', 'D'], 1),
                    ],
                }

            where the 4-tuple represents the

                RoundNm      - The round in which the tie-breaking event 
                                occurred.
                CandidateIds - The candidate IDs involved in the tie-breaking
                                event.
                Resolution   - The resolution for the tie-breaking event. May
                                be either a single candidate ID (cases 2, 3) 
                                or a permutation of the candidate IDs involved
                                in the tie-breaking event (case 1).
                CaseNm       - The case number identifying the type of tie-breaking
                                event (corresponds to the cases described above).

        (2) Construct a directed, acyclic graph where a directed edge from A to B 
            represents situations where A is elected over B (cases 1, 2) or B is 
            excluded (case 3). Note that more than one edge may be created by a 
            given tie-breaking event.

        (3) Sort the vertices into a linear order using a random topological sort.

        (4) Use the linear ordering discovered in Step 3 to break all ties
            encountered during the audit. In other words, given candidate IDs A and
            B, prefer electing/not-excluding the candidate earlier in the linear
            order.

Usage:

    .. code-block:: python3

        >>> import audit_tie_breaker
        >>> atb = AuditTieBreaker(['A', 'B', 'C', 'D', 'E', 'F', 'G'], verbose=True)
        >>> atb.load_events('contest_tie_breaking_events.json')
        = Building Audit Tie-Breaking Graph...
         - Case 1: Added edge B->C.
         - Case 1: Added edge B->A.
         - Case 1: Added edge C->A.
         - Case 3: Added edge D->E.
         - Case 3: Added edge F->E.
         - Case 2: Added edge G->D.
         --> Linear order determined as B, C, A, F, G, D, E.

        = Verifying linear order is consisent with real election's tie-breaking events...
         - Tie between ['A', 'B', 'C'] broken with ['B', 'C', 'A'] for case 1.
         - Tie between ['D', 'E', 'F'] broken with E for case 3.
         - Tie between ['D', 'G'] broken with G for case 2.
         --> Linear order is consistent with real election's tie-breaking events.

        >>> atb.break_tie(['A', 'B', 'C'], 1)
         - Tie between ['A', 'B', 'C'] broken with ['B', 'C', 'A'] for case 1.
"""

import itertools
import json
import os
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
    READ_OPT = 'r'
    WRITE_OPT = 'w'

    COMMA_DELIM = ', '

    EVENTS_KEY = 'events'

    EVENTS_FILE_ERROR_MSG = 'The file {0} is not formatted correctly. Expected: \
    { \'events\': [(<RoundNumber>, <CandidateIDs>, <Resolution>, <CaseNm>),]}'
    BUILDING_GRAPH_MSG = '= Building Audit Tie-Breaking Graph...'
    ADDED_EDGE_MSG = ' - Case {0}: Added edge {1}->{2}.'
    LINEAR_ORDER_MSG = ' --> Linear order determined as {0}.'
    VERIFY_LINEAR_ORDER_MSG = '\n= Verifying linear order is consisent with real election\'s tie-breaking events...'
    IS_CONSISTENT_MSG = ' --> Linear order is consistent with real election\'s tie-breaking events.\n'
    TIE_BREAK_MSG = ' - Tie between {0} broken with {1} for case {2}.'

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
        :type v: str or int
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

    def load_events(self, events_f):
        """ Loads all tie-breaking events specified in `events_f`.

        :param events_f: A string representing the name of a file to read all tie-
            breaking events from.
        :type events_f: str
        """
        # Read tie-breaking events from JSON file.
        with open(events_f, AuditTieBreaker.READ_OPT) as json_file:
            events = json.load(json_file).get(AuditTieBreaker.EVENTS_KEY)
            if events is None:
                raise Exception(AuditTieBreaker.EVENTS_FILE_ERROR_MSG.format(events_f))

        # Construct audit tie-breaking graph.
        self._print_fn(AuditTieBreaker.BUILDING_GRAPH_MSG)
        for event in events:
            try:
                round_num, candidate_ids, resolution, case_num = event
            except:
                raise Exception(AuditTieBreaker.EVENTS_FILE_ERROR_MSG.format(events_f))

            if len(resolution) == 1:
                # Cases 2, 3 - `resolution` is a single candidate ID.
                if case_num == 2:
                    for cid in candidate_ids:
                        if cid != resolution:
                            self._vertices[resolution].append(cid)
                            self._print_fn(AuditTieBreaker.ADDED_EDGE_MSG.format(2, resolution, cid))
                else:
                    for cid in candidate_ids:
                        if cid != resolution:
                            self._vertices[cid].append(resolution)
                            self._print_fn(AuditTieBreaker.ADDED_EDGE_MSG.format(3, cid, resolution))
            else:
                # Case 1 - `resolution` is a permutation of candidate IDs.
                for src_cid, dest_cid in itertools.combinations(resolution, 2):
                    self._vertices[src_cid].append(dest_cid)
                    self._print_fn(AuditTieBreaker.ADDED_EDGE_MSG.format(1, src_cid, dest_cid))

        # Determine a random topological sorting of the vertices in the audit tie-breaking graph.
        vertices = sorted(self._vertices.keys())
        random.shuffle(vertices)
        linear_order = []
        for v in vertices:
            self._visit(v, linear_order)
        self._linear_order = {linear_order[i] : i for i in range(len(linear_order))}
        self._print_fn(AuditTieBreaker.LINEAR_ORDER_MSG.format(AuditTieBreaker.COMMA_DELIM.join(linear_order)))

        # Verify linear order is consistent with the real election's tie-breakin events.
        self._print_fn(AuditTieBreaker.VERIFY_LINEAR_ORDER_MSG)
        for event in events:
            round_num, candidate_ids, resolution, case_num = event
            assert self.break_tie(candidate_ids, case_num) == resolution
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

        result = resolution          # Get permutation of candidates.
        if case_num == 2:
            result = resolution[0]   # Get candidate to elect.
        elif case_num == 3:
            result = resolution[-1]  # Get candidate to exclude.

        self._print_fn(AuditTieBreaker.TIE_BREAK_MSG.format(candidate_ids, result, case_num))
        return result


def test_audit_tie_breaker():
    """ Tests the `AuditTieBreaker` implementation. """
    # Setup tie-breaking events JSON to test implementation.
    TMP_TEST_EVENTS_JSON = 'tmp_test_tie_breaking_events.json'
    events = {
        'events': [
            (1, ['A', 'B', 'C'], ['B', 'C', 'A'], 1),
            (7, ['D', 'E', 'F'], 'E', 3),
            (12, ['D', 'G'], 'G', 2),
        ],
    }
    with open(TMP_TEST_EVENTS_JSON, 'w') as f:
        f.write(json.dumps(events))
    # Test `AuditTieBreaker` implementation.
    audit_tb = AuditTieBreaker(['A', 'B', 'C', 'D', 'E', 'F', 'G'], verbose=True)
    audit_tb.load_events(TMP_TEST_EVENTS_JSON)
    audit_tb._print_fn('= Running AuditTieBreaker tests...')
    assert audit_tb.break_tie(['A', 'B', 'C'], 1) == ['B', 'C', 'A']
    assert audit_tb.break_tie(['D', 'E', 'F'], 3) == 'E'
    assert audit_tb.break_tie(['D', 'G'], 2) == 'G'
    assert audit_tb.break_tie(['B', 'F'], 2) == 'B'  # Test depends on random.seed of 1.
    assert audit_tb.break_tie(['B', 'F'], 3) == 'F'  # Test depends on random.seed of 1.
    # Clean up temporary test data file.
    os.unlink(TMP_TEST_EVENTS_JSON)
    audit_tb._print_fn(' --> Tests PASSED!')


test_audit_tie_breaker()  # Runs AuditTieBreaker Tests.

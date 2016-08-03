# api_dividebatur.py
# Ronald L. Rivest
# July 31, 2016
# python3

"""
This is a draft API as a possible interface between the
Bayesian audit code (or other audit code) and the implementation
of the STV social choice function by Grahame Bowland.
"""

import copy
import hashlib
import os
import random

# Add parent directory to path so that we can find the dividebatur module.
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import dividebatur.dividebatur.senatecount as sc
from  dividebatur.dividebatur.counter import Ticket

##############################################################################
## Candidates

"""
A candidate is represented by the Candidate named-tuple datatype 
as defined in dividbatur senatecount.py. A candidate has attributes:
    CandidateID                 # integer
    Surname                     # string
    GivenNm                     # string
    PartyNm                     # string
"""

##############################################################################
## Ballot (preference tuple)

""" 
A ballot is a tuple of candidate_ids, in order of decreasing preference.
It may have any length, possibly less than the number of candidates; 
candidates not mentioned are preferred less than those mentioned.
One may think of this as the (BTL) form of a single cast paper ballot.

(It could alternatively be a tuple of (preference_no, candidate_id) pairs,
as long as it is hashable, and things are sorted into order.  But I prefer
the simpler tuple of candidate_ids.)
"""

##############################################################################
## Election

class Election:
    """
    An Election represents the basic information about an election, 
    including candidates, number of seats available, list of cast
    ballots (with multiplicities), etc.
    """

    ID = 'id'
    SCF = 'method'
    ORDER = 'order'
    FORMAT = 'format'
    CONTESTS = 'count'
    ELECTED = 'elected'
    CONTEST_NAME = 'name'
    ELECTION_ID = 'title'
    AEC_DATA = 'aec-data'
    VERIFY_FLAG = 'verified'
    NUM_VACANCIES = 'vacancies'

    def __init__(self, tie_break_string='TIE_BREAK_STRING'):
        self.electionID = "NoElection"       # string
        self.n = 0                           # integer
        self.seats = 0                       # integer
        self.candidate_ids = []              # list of candidate_ids
        self.candidates = []                 # list of candidates
        self.ballots = []                    # list of ballots drawn so far
        self.ballots_drawn = 0               # integer
        self.ballot_weights = {}             # dict mapping ballots to weights
        self.total_ballot_weight = 0.0       # sum of all ballot weights
        self.remaining_tickets = []          # list of remaining tickets to draw ballots from.

        # `dividebatur` specific variables.
        self.out_dir = None                  # string representing the directory path for writing election results
        self.data_dir = None                 # string representing the directory path containing the election data
        self.contest_config = None           # dict containing contest-specific information (i.e. number of seats)
        self.data = None                     # data structure storing contest tickets, candidates, SCF, etc.

        self.tie_break_string = tie_break_string  # string used in breaking ties related to the election

        """
        Remarks:

         * `self.ballot_weights` is a python dict mapping ballots in `self.ballots` to weights that are
        >= 0. These weights are *not* modified by the counting; they always represent the number of times 
        each preference list was input as a ballot. These weights need *not* be integers.
         * `self.remaining_tickets` is a list of all tickets in the election contest. This list is modified
        when ballots are drawn at random to grow an audit sample. Note that there may be duplicates of the
        same ballot in `self.remaining_tickets` (i.e. multiplicities are expanded).
        """

    def load_election(self, contest_name, config_file=None, out_dir=None):
        """
        Load election data for the contest with the provided name using the provided configuration file name. Sets

            self.electionID
            self.seats
            self.candidate_ids
            self.candidates
            self.remaining_tickets

        As well as `dividebatur`-specific instance variables

            self.out_dir
            self.data_dir
            self.contest_config
            self.data

        Remarks:

         * Formality checks are performed as the initial data is being loaded and processed by `dividebatur`.    
         * `dividebatur` handles all ATL to BTL conversions. The `self.remaining_tickets` contains BTL ballots.
        """

        # Sets configuration file and out directory to default values if not set by caller.
        config_file = config_file or '../dividebatur/aec_data/fed2016/aec_fed2016.json'
        self.data_dir = os.path.dirname(os.path.abspath(config_file))
        self.out_dir = out_dir or '../dividebatur/angular/data/'

        # Read the configuration file for the election data.
        election_config = sc.read_config(config_file)
        self.electionID = election_config[Election.ELECTION_ID]

        # An election may have multiple contests. Here we select the contest with the provided
        # contest name (e.g. 'TAS' or 'NT', for Tasmania and Northern Territory, respecitvely).
        self.contest_config = next((contest for contest in election_config[Election.CONTESTS] if contest[Election.CONTEST_NAME] == contest_name), None)
        if self.contest_config is None:
            possible_names = ', '.join([contest[Election.CONTEST_NAME] for contest in election_config[Election.CONTESTS]])
            raise Exception('Contest with name %s not found. Try one of %s.' % (contest_name, str(possible_names)))

        # Get the number of seats for this contest.
        self.seats = self.contest_config[Election.NUM_VACANCIES]

        # Get the social chocie function.
        input_cls = sc.get_input_method(self.contest_config[Election.AEC_DATA][Election.FORMAT])

        try:
            # Remove this key to suppress verification checks which would
            # not be valid for a subsample of the ballots from the contest.
            del self.contest_config[Election.VERIFY_FLAG]
        except KeyError:
            pass

        # Prepare filesystem to accept output of running election audits.
        sc.cleanup_json(self.out_dir)
        sc.write_angular_json(election_config, self.out_dir)

        # Get ticket data.
        s282_candidates = sc.s282_recount_get_candidates(self.out_dir, self.contest_config, set())
        self.data = sc.get_data(input_cls, self.data_dir, self.contest_config, s282_candidates=s282_candidates)

        # Build remaining ticket data structure from tickets and randomly shuffle for sampling.
        for ticket, weight in self.data.tickets_for_count:
            # NOTE: We expand multiplicities here such that for each ticket, there are `weight` copies of that ticket 
            # in `self.remaining_tickets`. We do this for ease of random sampling (e.g. note that a dictionary mapping
            # tickets to their corresponding weights does not facilitate easy random sampling).
            for _ in range(weight):
                self.remaining_tickets.append(copy.deepcopy(ticket))
            self.n += weight
        print('Total number of ballots in contest:', self.n)
        random.shuffle(self.remaining_tickets)

        # Get candidate data.
        self.candidate_ids = self.data.get_candidate_ids()
        self.candidates = self.data.candidates.candidates
    
    def add_ballot(self, ballot, weight):
        """ 
        Add BTL ballot with given weight to the election.
        If ballot with same preferences already exists, then
        just add to its weight.  
        No formality checks are made.
        """

        if ballot in self.ballot_weights:
            self.ballot_weights[ballot] += weight
        else:
            self.ballots.append(ballot)
            self.ballot_weights[ballot] = weight
        self.total_ballot_weight += weight

    def convert_ticket_to_ballot(self, ticket):
        """
        `ticket.preferences` is a tuple containing a single tuple of (rank, candidate_id) pairs. 
        We then convert this representation to a tuple of candidate IDs, sorted by rank.
        """

        preferences = sorted(ticket.preferences, key=lambda x : x[0])
        return tuple(candidate_id for rank, candidate_id in preferences)

    def load_more_ballots(self, batch_size):
        """ 
        Expand the current sample by `batch_size` by adding each new BTL ballot with a weight of 1.
        """

        # Make sure not to over draw remaining ballots.
        ballots_to_draw = min(batch_size, len(self.remaining_tickets))
        for _ in range(ballots_to_draw):
            # Pop off the first ticket in `self.remaining_tickets`, convert it from a ticket to a ballot,
            # and finally add it to the growing sample of ballots.
            self.add_ballot(self.convert_ticket_to_ballot(self.remaining_tickets.pop(0)), 1)
        self.ballots_drawn += ballots_to_draw

    def get_outcome(self, new_ballot_weights=None, **params):
        """ 
        Return list of candidates who are elected in this election, where
        self.ballot_weights gives weights of each ballot.

        However, if new_ballot_weights is given, use those instead 
        of self.ballot_weights.

        params is dict giving parameters that may affect how computation
        is done, such as tie-breaking info, or number n of ballots cast overall
        in election (not just sample size).

        params may also control output (e.g. logging output).
        """
        def tie_break_by_sha256_sort(items):
            """
            `tie_break_by_sha256_sort` takes a list of items. It then converts every item in the
            list to a string and concatenates that string with the tie break string. This concatenation
            is then unicode encoded and the SHA-256 is taken. These hashes are then converted to HEX and
            sorted lexicographically. Finally, the original index of the first item in this sorted list
            of hashes is returned as the index of the item to chose for breaking the given tie. Here the
            original index refers to the item's position in the input `items`.
            """
            def get_sha256_hash_of_item(item):
                return hashlib.sha256((str(item) + self.tie_break_string).encode('utf-8')).hexdigest()

            indices = sorted(range(len(items)), key=lambda i : get_sha256_hash_of_item(items[i]))
            return indices[0]

        ballot_weights = new_ballot_weights or self.ballot_weights

        # Reset tickets for count 
        self.data.tickets_for_count = sc.PapersForCount()
        for ballot, weight in ballot_weights.items():
            # Build list of preferences as (rank, candidate_id) tuple pairs.
            preferences = [(i, ballot[i - 1]) for i in range(1, len(ballot) + 1)]
            ticket = Ticket(preferences)
            self.data.tickets_for_count.add_ticket(ticket, weight)

        _, outcome = sc.get_outcome(self.contest_config, self.data, self.data_dir, self.out_dir, automation_fn=tie_break_by_sha256_sort)
        return tuple(sorted(electee[Election.ID] for electee in outcome[Election.ELECTED]))

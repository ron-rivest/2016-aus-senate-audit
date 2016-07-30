# api.py
# Ronald L. Rivest
# July 29, 2016
# python3

"""
This is a draft API as a possible interface between the
Bayesian audit code (or other audit code) and the implementation
of the STV social choice function by Grahame Bowland.
"""


##############################################################################
## Candidates

"""
A candidate is represented by  the Candidate named-tuple datatype 
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

    def __init__(self):
        self.electionID = "NoElection"       # string
        self.seats = 0                       # integer
        self.candidate_ids = []              # list of candidate_ids
        self.candidates = []                 # list of candidates
        self.ballots = []                    # list of ballots
        self.ballot_weights = {}             # dict mapping ballots to weights
        self.total_ballot_weight = 0.0       # sum of all ballot weights
        """
        ballot_weights is a python dict mapping ballots in self.ballots to weights that are >= 0.
        These weights are *not* modified by the counting; they always
        represent the number of times each preference list was input as a ballot.
        These weights need *not* be integers.
        """

    def load_election(self, dirname):
        """
        Load election data from files in the specified directory. Sets
            self.electionID
            self.seats
            self.candidate_ids
            self.candidates
            self.ballots
            self.ballot_weights    
        No formality checks are made.
        Translates each ATL ballot into a BTL equivalent.
        """

        pass # TBD
    
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

    def load_more_ballots(self, filename):
        """ 
        repeat add_ballot on each new BTL ballot from file with given filename, 
        each with weight 1 
        """

        pass # TBD

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

        pass # TBD

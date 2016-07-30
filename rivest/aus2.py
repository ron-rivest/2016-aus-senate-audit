# aus2.py
# July 27, 2016
# python3
# code sketches for AUS senate audit by Bayesian audit method
# This codes derives from aus.py, but modified to utilize api.py
# for interfacing with dividebatur code.
# It also is being modified to use gamma-variate optimization.

import collections
import copy
import random
# random.seed(1)    # make deterministic

import api

class RealElection(api.Election):

    def __init__(self):
        super(RealElection, self).__init__()
        self.candidates = []
        self.prior_ballots = [ (c,) for c in self.candidates ]

    def get_candidates(self):
        return []

    def draw_ballots(self, k):
        """ 
        return list of up to k paper ballots 
        """
        return None

    def get_outcome(self, sample):
        """ Return result of scf (social choice function) on this sample. """
        ### call Bowland's code here
        return None

class SimulatedElection(api.Election):

    def __init__(self, m, n):
        super(SimulatedElection, self).__init__()
        self.m = m                                 # number of candidates
        self.candidates = list(range(1,self.m+1))  # {1, 2, ..., m}
        self.candidate_ids = list(range(1,self.m+1))  # {1, 2, ..., m}
        self.n = n                                 # number of cast ballots
        self.ballots_drawn = 0                     # cumulative

    def draw_ballots(self, k):
        """ 
        add to ballots up to k simulated ballots for testing purposes 
        or [] if no more ballots available
        These ballots are biased so (1,2,...,m) is likely to be the winner
        More precisely, for each ballot candidate i is given a value i+v*U
        where U = uniform(0,1).  Then candidates are sorted into increasing
        order of these values.
        """
        v = 5.0   # noise level
        k = min(k, self.n-self.ballots_drawn)
        for _ in range(k):
            L = [ (idx + v*random.random(), c)
                  for idx, c in enumerate(self.candidates) ]
            ballot = tuple(c for (val, c) in sorted(L))
            self.add_ballot(ballot, 1.0)
        self.ballots_drawn += k
    
    def get_outcome(self, new_ballot_weights):
        """ 
        Return result of scf (social choice function) on this sample. 

        Here we use Borda count as a scf.
        Returns tuple in decreasing order of candidate popularity.
        """
        counter = collections.Counter()
        for ballot in self.ballots:
            w = new_ballot_weights[ballot]
            for idx, candidate_id in enumerate(ballot):
                counter[candidate_id] += w*idx
        L = counter.most_common()
        L.reverse()
        return tuple(c for (c, count) in L)


##############################################################################
# A ballot is an abstract blob.
# Here implemented as a tuple.
# The only operations we need on ballots are:
#    -- obtaining them from election data
#    -- putting them into a list
#    -- copying one of them
#    -- making up a list of "prior ballots" expressing
#       our Bayesian prior
#    -- (possibly re-weighting ballots?)

##############################################################################
# Implementation of polya's urn or equivalent

def get_new_ballot_weights(election, r):
    """ 
    Return dict new_ballot_weights for this election, based
    on using gamma variates to give us Dirichlet distribution over
    existing ballots, based on existing ballot weights.
    Sum of new ballot weights should be r (approximately).
    New weights are rounded down.
    """

    new_ballot_weights = {}
    for ballot in election.ballots:
        old_weight = election.ballot_weights[ballot]
        new_ballot_weights[ballot] = random.gammavariate(old_weight,1.0)
    total_weight = sum([new_ballot_weights[ballot]
                        for ballot in election.ballots])
    for ballot in election.ballots:
        new_ballot_weights[ballot] = int(r * new_ballot_weights[ballot] / total_weight)
    return new_ballot_weights
    
##############################################################################
# Implementation of audit

def audit(election, alpha=0.05, k=4, trials=100):
    """ 
    Bayesian audit of given election 

    Input:
        election     # election to audit
        alpha        # error tolerance
        k            # amount to increase sample size by
        trials       # trials per sample
    """
    print("audit")
    print("Candidates are:", election.candidates)
    print("Number of ballots cast:", election.n)
    print("Number of trials per sample:", trials)

    # overall audit loop
    sample = []
    while True:

        # cast one "prior ballots" ballot for each candidate, to
        # establish Bayesian prior.  The prior ballot is a length-one
        # partial ballot with just a vote for that candidate.
        for c in election.candidate_ids:
            election.add_ballot((c,),1.0)

        # draw additional ballots and add them to election.ballots
        election.draw_ballots(k)   

        print("sample size is now", len(election.ballots),"(including prior ballots):")

        # run trials in Bayesian manner
        # we assume that each outcome is 
        # a list or tuple of candidates who have been elected, 
        # in some sort of canonical or sorted order.
        # We can thus test for equality of outcomes.
        outcomes = []
        for _ in range(trials):
            new_ballot_weights = get_new_ballot_weights(election, election.n)
            outcomes.append(election.get_outcome(new_ballot_weights))

        # find most common outcome and its number of occurrences
        best, freq = collections.Counter(outcomes).most_common(1)[0]
        print("    most common winner =",best, "freq =",freq)

        # stop if best occurs almost always
        if freq >= trials*(1.0-alpha):
            print("Stopping: audit confirms outcome:", best)
            break

        if len(election.ballots) == election.n:
            print("Audit has looked at all ballots. Done.")
            break

audit(SimulatedElection(4,10000))

          
        
    

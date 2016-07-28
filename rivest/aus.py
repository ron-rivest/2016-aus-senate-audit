# aus.py
# July 27, 2016
# python3
# code sketches for AUS senate audit by Bayesian audit method

import collections
import copy
import random
# random.seed(1)    # make deterministic

class Election:
    pass

class RealElection(Election):

    def __init__(self):
        self.candidates = []
        self.prior_ballots = [ (c,) for c in self.candidates ]

    def get_candidates(self):
        return []

    def draw_ballots(self, k):
        """ 
        return list of up to k paper ballots 
        """
        return None

    def scf(self, sample):
        """ Return result of scf (social choice function) on this sample. """
        ### call Bowland's code here
        return None

class SimulatedElection(Election):

    def __init__(self, m, n):
        self.m = m                                 # number of candidates
        self.candidates = list(range(1,self.m+1))  # {1, 2, ..., m}
        self.n = n                                 # number of cast ballots
        self.prior_ballots = [ (c,) for c in self.candidates ] # one for each

    def draw_ballots(self, k):
        """ 
        return list of up to k simulated ballots for testing purposes 
        or [] if no more ballots available
        """
        if random.random()<0.01:
            return []
        ballots = []
        for _ in range(k):
            ballot = list(self.candidates[:])
            random.shuffle(ballot)
            ballots.append(ballot)
        return ballots
    
    def scf(self, sample):
        """ 
        Return result of scf (social choice function) on this sample. 

        Here we use Borda count as a scf.
        Returns tuple in decreasing order.
        """
        counter = collections.Counter()
        for ballot in sample:
            for idx, candidate in enumerate(ballot):
                counter[candidate] += idx
        return tuple(c for (c, count) in counter.most_common())


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

def copy_ballot(b):
    return copy.deepcopy(b)


##############################################################################
# Implementation of polya's urn

def urn(election, sample, r):
    """ 
    Return list of length r generated from sample and prior ballots.

    Don't return prior ballots, but sample is part of returned result.
    It may be possible to optimize this code using gamma variates.
    """

    L = election.prior_ballots + sample
    for _ in range(r-len(sample)):
        L.append(copy_ballot(random.choice(L)))
    return L[len(election.prior_ballots):]

def test_urn(election):
    k = 5
    r = 10
    print("test_urn",k, r)
    sample = election.draw_ballots(k)
    print(urn(election, sample, r))

test_urn(SimulatedElection(3,36))

##############################################################################
# Implementation of audit

def audit(election, alpha=0.05, k=4, trials=20):
    """ 
    Bayesian audit of given election 

    Input:
        election     # election to audit
        alpha        # error tolerance
        k            # amount to increase sample size by
        trials       # trials per sample
    """
    print("audit")

    # get basic election info
    candidates = election.candidates
    n = election.n               

    # overall audit loop
    sample = []
    while True:

        # draw additional ballots and add them to sample
        sample_increment = election.draw_ballots(k)   

        if sample_increment is []:
            print("Audit has looked at all ballots. Done.")
            break

        sample.extend(sample_increment)
        print("sample size is", len(sample))
        # print("sample is:", sample)

        # run trials in Bayesian manner
        outcomes = [election.scf(urn(election, sample, n))
                    for t in range(trials)]
        # we assume that each outcome is 
        # a list or tuple of candidates who have been elected, 
        # in some sort of canonical or sorted order.
        # We can thus test for equality of outcomes.

        # find most common outcome and its number of occurrences
        best, freq = collections.Counter(outcomes).most_common(1)[0]
        print(best, freq)

        # stop if best occurs almost always
        if freq >= trials*(1.0-alpha):
            print("Stopping: audit confirms outcome:", best)
            break

audit(SimulatedElection(4,100))

          
        
    

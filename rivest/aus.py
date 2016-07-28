# aus.py
# July 27, 2016
# python3
# code sketches for AUS senate audit by Bayesian audit method

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
        self.candidates = list(range(1,self.m+1))
        self.n = n                                 # number of cast ballots
        self.prior_ballots = [ (c,) for c in self.candidates ]

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
        """ Return result of scf (social choice function) on this sample. """
        # TBD
        return tuple(self.candidates)

##############################################################################
# A ballot is an abstract blob.
# Here implemented as a tuple.
# The only operations we need on ballots are:
#    -- obtaining them from election data
#    -- putting them into a list
#    -- copying one of them
#    -- making up a list of "prior ballots" expressing
#       our Bayesian prior

def copy_ballot(b):
    return copy.deepcopy(b)


##############################################################################
# Implementation of polya's urn

def urn(election, sample, r):
    """ 
    Return list of length r generated from sample and prior ballots 
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

def audit(election):
    """ Bayesian audit of given election """

    print("audit")

    # get basic election info
    candidates = election.candidates
    n = election.n               

    # control parameters
    alpha = 0.05          # error tolerance
    k = 4                 # amount to increase sample size by
    trials = 20           # per sample

    # overall audit loop
    sample = []
    while True:

        sample_increment = election.draw_ballots(k)
        if sample_increment is None:
            print("Audit has looked at all ballots. Done.")
            break
        sample.extend(sample_increment)
        print("sample is:", sample)

        # run trials in Bayesian manner
        outcomes = []
        for t in range(trials):
            full_urn = urn(election, sample, n)
            outcomes.append(election.scf(full_urn))

        # figure out whether to stop or not based on outcomes
        # fake it for now
        if random.random()<(float(len(sample))/float(n)):
            print("Audit confirms outcome; stop.")
            break
        # TBD: stop if some outcome happened more than trials*(1-alpha) times

audit(SimulatedElection(4,100))

          
        
    

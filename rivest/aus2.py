# aus2.py
# July 30, 2016
# python3
# part of https://github.com/ron-rivest/2016-aus-senate-audit

# framework for AUS senate audit by Bayesian audit method
# This codes derives from aus.py, but modified to utilize api.py
# for interfacing with dividebatur code.
# It has also been modified to use gamma-variates to draw from
# Dirichlet posterior probability distribution, rather than using
# Polya's urn method, for efficiency reasons.

import collections
import random
# random.seed(1)    # make deterministic
import time

import api

class RealElection(api.Election):

    def __init__(self):
        super(RealElection, self).__init__()
        api.load_election(self, "dirname-TBD")

    def draw_ballots(self, batch_size=100):
        """ 
        add interpretation of random sample of real ballots
        to election data structure
        """
        api.load_more_ballots(self, "filename-TBD")

    def get_outcome(self, new_ballot_weights):
        """ 
        Return result of scf (social choice function) on this election. 
        """
        ### call Bowland's code here
        pass

class SimulatedElection(api.Election):

    def __init__(self, m, n):
        super(SimulatedElection, self).__init__()
        self.m = m                                 # number of candidates
        self.candidates = list(range(1,self.m+1))  # {1, 2, ..., m}
        self.candidate_ids = list(range(1,self.m+1))  # {1, 2, ..., m}
        self.n = n                                 # number of cast ballots
        self.ballots_drawn = 0                     # cumulative
        self.seats = int(m/2)                      # seat best 1/2 of candidates
        self.electionID = "SimulatedElection " + \
                          time.asctime(time.localtime())

    def draw_ballots(self):
        """ 
        add simulated ballots (sample increment) for testing purposes 
        These ballots are biased so (1,2,...,m) is likely to be the winner
        More precisely, for each ballot candidate i is given a value i+v*U
        where U = uniform(0,1).  Then candidates are sorted into increasing
        order of these values.
        Does not let total number of ballots drawn exceed the total
        number n of cast votes.
        Default batch size otherwise is 100.
        """
        m = self.m                                 # number of candidates
        v = m/2.0                                  # noise level (control position variance)
        default_batch_size = 100                   
        batch_size = min(default_batch_size,
                         self.n-self.ballots_drawn) 
        for _ in range(batch_size):
            L = [ (idx + v*random.random(), candidate_id)
                  for idx, candidate_id in enumerate(self.candidate_ids) ]
            ballot = tuple(candidate_id for (val, candidate_id) in sorted(L))
            self.add_ballot(ballot, 1.0)
        self.ballots_drawn += batch_size
    
    def get_outcome(self, new_ballot_weights):
        """ 
        Return result of scf (social choice function) on this sample. 

        Here we use Borda count as a test scf.
        Returns tuple listing candidate_ids of winners in canonical (sorted) order,
        most preferred to least preferred.  The number of winners is equal
        to self.seats.  Each ballot carries a weight equal to new_ballot_weights[ballot].
        """

        counter = collections.Counter()
        for ballot in self.ballots:
            w = new_ballot_weights[ballot]
            for idx, candidate_id in enumerate(ballot):
                counter[candidate_id] += w*idx
        L = counter.most_common()
        L.reverse()
        L = [candidate_id for (candidate_id, count) in L]
        outcome = tuple(sorted(L[:self.seats]))
        return outcome


##############################################################################
# Drawing from Bayesian posterior (aka reweighting or fuzzing)

def get_new_ballot_weights(election, r):
    """ 
    Return dict new_ballot_weights for this election, based
    on using gamma variates to draw from Dirichlet distribution over
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
    print()
    print("Audit of simulated election")
    print("ElectionID:",election.electionID)
    print("Candidates are:", election.candidates)
    print("Number of ballots cast:", election.n)
    print("Number of trials per sample:", trials)
    print("Number of seats contested for:",election.seats)
    seed = int(random.random()*1000000000000)
    random.seed(seed)
    print("Random number seed:", seed)    # for reproducibility or debugging if needed
    print()

    # cast one "prior" ballot for each candidate, to
    # establish Bayesian prior.  The prior ballot is a length-one
    # partial ballot with just a first-choice vote for that candidate.
    for c in election.candidate_ids:
        election.add_ballot((c,),1.0)

    start_time = time.time()

    # overall audit loop
    stage_counter = 0
    while True:
        stage_counter += 1
        print("Audit stage number:", stage_counter)

        # draw additional ballots and add them to election.ballots
        election.draw_ballots()   

        print("    sample size (including prior ballots) is",
              election.total_ballot_weight)
        print("    last ballot drawn:")
        print("        ",election.ballots[-1])

        # run trials in Bayesian manner
        # Each outcome is a tuple of candidates who have been elected, 
        # in a canonical order. (NOT the order in which they were elected, say.)
        # We can thus test for equality of outcomes.
        print("    doing",trials,"Bayesian trials (posterior-based election simulations) in this stage.")
        outcomes = []
        for _ in range(trials):
            new_ballot_weights = get_new_ballot_weights(election, election.n)
            outcomes.append(election.get_outcome(new_ballot_weights))

        # find most common outcome and its number of occurrences
        best, freq = collections.Counter(outcomes).most_common(1)[0]
        print("    most common outcome (",election.seats,"seats ):")
        print("        ", best)
        print("    frequency of most common outcome:",freq,"/",trials)

        # stop if best occurs almost always (more than 1-alpha of the time)
        if freq >= trials*(1.0-alpha):
            print()
            print("Stopping: audit confirms outcome:")
            print("    ", best)
            print("Total number of ballots examined:", election.ballots_drawn)
            break

        if election.ballots_drawn >= election.n:
            print("Audit has looked at all ballots. Done.")
            break

        print()

    print("Elapsed time:",time.time()-start_time,"seconds.")

audit(SimulatedElection(100,1000000))

          
        
    

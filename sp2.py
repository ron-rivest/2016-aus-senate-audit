# sp2.py
# Ronald L. Rivest (joint work with Kate Yu)
# July 24, 2016

# Basic problem:
#    Sample a profile according to given marginals (pairwise preferences)
#    (Def: a profile is a set of ballots. Really a list or multi-set.)
#    Ballots are preferential ballots: list of candidates in decreasing
#       order of preference.
#    Marginals are m x m matrix A (where m = number of candidates) showing
#       number A[i][j] of ballots preferring candidate i to candidate j.

# Application:
#    Auditing: E.g. "black-box post-election auditing" (ref Rivest/Stark)
#              Draw a sample S of ballots from collection of cast ballots
#              Let f = social choice function computing winner for profile
#              Compute f(S) = W, the sample winner
#              Compute S_1, S_2, ..., S_T  as "variants" of S
#              Compute W_k = f(S_k) for k = 1, 2, ..., T
#              Accept W as correct if W_k = W for k = 1, 2, ..., T and
#                  if W is the reported winner of the election, too.
#              Otherwise increase size of sample S. Rinse and repeat.

# To compute variants of S:
#   Given a set (sample) B of preferential ballots for m candidates
#   Compute pairwise preferences (A[i][j] is number preferring i to j)
#   Tweak pairwise preferences to get profile Bk "somewhat like" B.
#       Treat each pair Bk[i][j], Bk[j][i] as drawn from beta distribution.
#           Note that Bk[i][j] + Bk[j][i] is constant = # of ballots n.
#   Derive profile of ballots for Bk using Tideman's ranked-pairs method
#       as subroutine.

import copy
import random

try:
    import scipy.stats
    beta = scipy.stats.beta
except ImportError:
    # This is necessary when using pypy, because there's no scipy
    pass

import numpy

##############################################################################
## Ensure that all randomness here is "pseudo", so results are consistent
##############################################################################
random.seed(1)            # Make results deterministic.
numpy.random.seed(1)      # Make results deterministic.

##############################################################################
## compute preference matrix from a profile of ballots
##############################################################################

def prefs(B):
    """ 
    Input B is a list of ballots; each ballot is a permutation of range(m).
    Return matrix A of prefs according to ballots in B 
    A[a][b] is number of ballots preferring a to b
    """

    m = len(B[0])

    for ballot in B:
        assert sorted(ballot) == range(m)

    A = [ [0 for j in range(m)] for i in range(m) ]
    for ballot in B:
        for i in range(m):
            a = ballot[i]
            for j in range(i+1, m):
                b = ballot[j]
                A[a][b] += 1
    return A 

##############################################################################
## sample profiles for testing
##############################################################################

B1 = [ [0, 1, 2, 3],
       [1, 2, 0, 3],
       [3, 1, 2, 0],
       [1, 3, 0, 2],
       [2, 1, 0, 3]]

B2 = [ [ 0, 1, 2 ],
       [ 2, 1, 0 ]]

B3 = [ [ 0, 1, 2, 3, 4 ],
       [ 1, 2, 3, 4, 0 ],
       [ 1, 3, 4, 2, 0 ] ]

B4 = [ [   0, 1, 2, 3 ],             # cyclic !
       [   1, 2, 3, 0 ],
       [   2, 3, 0, 1 ],
       [   3, 0, 1, 2 ]] * 100

B5 = []
for _ in range(500):
    ballot = range(5)
    random.shuffle(ballot)
    B5.append(ballot)


##############################################################################
## beta distributions
##############################################################################

def sn(n, sk, fk):
    """ 
    Input sk = number of successes observed in k trials (k = sk+fk) 
    Input fk = number of failures observed in k trials  (k = sk+fk)
    Input n = number of trials yet to see
    Ouput (sn, fn) = rv number of trials that may succeed/fail in those n trials
                     (integers between 0 and n, inclusive, with n=sn+fn
                     This is a randomized procedure, producing random output.
    Method: use beta distribution to predict p, then scale to range(0,n+1).
    """
    bd = beta(sk+1, fk+1)                     # create beta distribution
    assert n >= 0
    p = bd.rvs()                              # draw p from beta distribution
    sn = int(p*(n+1))
    if sn>n:                                  # could only happen if p = 1.000 !
        sn = n
    fn = n - sn
    return (sn, fn)

def sn_matrix(A, n):
    """
    Input: m x m matrix A of nonnegative numbers (0's on diag)
    Output: "Similar" matrix AA, with AA[i][j] + AA[j][i] == n
    """
    m = len(A)
    assert all([m == len(A[i]) for i in range(m)])
    assert all([A[i][i]==0 for i in range(m)])
    assert all([A[i][j]>=0 for i in range(m) for j in range(m)])

    AA = [[0 for j in range(m)] for i in range(m)]
    for i in range(m):
        for j in range(i+1,m):
            s = A[i][j]
            f = A[j][i]
            AA[i][j], AA[j][i] = sn(n, s, f)
    return AA

def test_sn_matrix():
    A = [ [ 0,  1,  2  ],
          [ 3,  0,  25 ],
          [ 100, 25, 0 ]]
    print A
    for _ in range(10):
        print sn_matrix(A, 100)

# test_sn_matrix()        

##############################################################################
## end of beta distribution
##############################################################################

##############################################################################
## implementation of Tideman's ranked pairs method (RP)
##############################################################################

def sorted_pairs(A):
    """ 
    Input A is an m x m matrix of pairwise preferences (numbers)
          A[i][j] is number of voters preferring i to j
    Output is a sorted list of pairs, decreasing order of strength.
    (Ties broken using random numbers as tie-breakers.)
    """
    m = len(A[0])
    V = range(m)
    L = [(A[i][j], random.random(), i, j) for i in V for j in V if i != j ]
    L = sorted(L, reverse=True)
    matches = 0
    for x in xrange(len(L)-1):
        if L[x][0] is not L[x+1][0]:
            break
        else:
            matches += 1
    #if matches is not 0:
        # print L
        #print "There was a %d-way tie" % matches
    return [(i,j) for (Aij, rand, i, j) in L]

def test_sorted_pairs():
    A = [ [ 0, 6, 9 ],
          [ 7, 0, 11 ],
          [ 13, 12, 0 ]]
    assert sorted_pairs(A) == \
        [(2, 0), (2, 1), (1, 2), (0, 2), (1, 0), (0, 1)]
    # assertion always true since there are no ties...

test_sorted_pairs()

def reachable(Adj, s, t):
    """
    Adj is adjacency list rep of graph
    Return True if edges in Adj have directed path from s to t.

    Note that this routine is one of the most-used and most time-consuming
    of this whole procedure, which is why it is passed an adjacency list 
    rep rather than a list of vertices and edges, since the adjacency list
    rep is easy to update when a new edge is committed to in RP.
    """
    # search for path
    Q = [ s ]         # vertices to expand
    R = set([s])      # reachable
    while Q:
        i = Q.pop()
        for j in Adj[i]:
            if j == t:
                return True
            if j not in R:
                R.add(j)
                Q.append(j)
    return False

def test_reachable():
    V = range(6)
    E = [ (1,2), (1,3), (2, 3), (3, 2), (3,4), (4,3), (4, 1), (4,5), (0,5) ]
    assert reachable(V, E, 1, 5)
    assert not reachable(V, E, 1, 6)

# test_reachable()  ### NO LONGER GOOD TEST ROUTINE GIVEN CHANGE TO REACHABLE INTERFACE

def RP(A):
    """ 
    Ranked-pairs algorithm.
    Input A is m x m preference matrix.
    Output is ordered list of candidates. (Most favored first)
    Labels assumed to be from range(m)
    """
    m = len(A)
    V = range(m)
    E = sorted_pairs(A)
    CE = [ ]                      # committed edges
    Adj = { i:[] for i in V }     # adj list for committed edges
    for (i,j) in E:
        if not reachable(Adj, j, i):
            CE.append((i,j))
            Adj[i].append(j)
    beats = { i:0 for i in V }    # number that i beats
    for (i,j) in CE:
        beats[i] += 1
    L = [ (beats[i], i) for i in V ]
    L = sorted(L, reverse=True)
    return [ i for (c, i) in L ]

def test_RP():               
    A = [ [ 0, 6, 9 ], \
          [ 7, 0, 11 ], \
          [ 13, 12, 0 ]]
    assert RP(A) == [2, 1, 0]

#test_RP()

##############################################################################
## end of ranked-pairs (RP) implementation
##############################################################################

##############################################################################
## generate profile of size n of ballots that is similar in terms of
## preferences represented by a pairwise preference matrix A
##############################################################################
def generate_tweaked_profile(A, n, printing_wanted=True):
    """ 
    Input: A is a pairwise preference matrix where A[i][j] is the number of voters
           that prefer candidate i to j.
           n is desired number of ballots to generate and return.
    Output: list S of n ballots that are "like" those in B,
            in the sense that matrix of prefs for S is close to 
            (percentage-wise) those in B. 
            (Some variations on prefs are deliberately added for variability.)
    """
    if printing_wanted:
        print "Preference matrix A of provided ballots (before tweaking):"
        for row in A:
            print row
    A = sn_matrix(A, n)    # make a noisy version of A
    generate_profile(A, n, printing_wanted)

def generate_profile(A, n, printing_wanted=True):
    m = len(A[0])
    if printing_wanted:
        print "Preference matrix A of provided ballots:"
        for row in A:
            print row

    S = []            # list of generated ballots
    d = dict()        # maps generated ballots to counts
       
    A2 = [[0 for j in range(m)] for i in range(m)]  # prefs for generated ballots

    needs = [ [ A[i][j] \
                for j in range(m) ] for i in range(m) ]

    target = copy.deepcopy(needs)

    if printing_wanted:
        print "target profile matrix for ballots to be generated:"
        for i, row in enumerate(needs):
            print "%2d: "%i,
            for item in row:
                print "%6d "%int(item),
            print

    while len(S) < n:
        # generate p as new ballot using RP
        p = RP(needs)
        S.append(p)
       
        # update counts in d, if m is not too large
        if m <= 12:
            pt = tuple(p)
            d[pt] = d.get(pt,0) + 1

        # now update prefs and needs
        for i in range(m):
            a = p[i]
            for j in range(i+1, m):
                b = p[j]
                A2[a][b] += 1
                needs[a][b] -= 1

    if printing_wanted:
        print "actual preference matrix for ballots generated:"
        for i, row in enumerate(A2):
            print "%2d: "%i,
            for c in row:
                print "%6d "%c,
            print
    print "differences in matrix entries from desired matrix:"
    difference_matrix = []
    for x in xrange(len(A2)):
        a2_row = A2[x]
        target_row = target[x]
        difference_matrix.append([])
        print "%2d: " %x,
        for c1, c2 in zip(a2_row, target_row):
            difference_matrix[x].append(abs(c1-c2))
            print "%6d " %(c1-c2),
        print
    print "sum of absolute values of deviations:"
    deviations = sum(map(sum, difference_matrix))
    print deviations
    return deviations

    # if m>12:
    #     return
    #if printing_wanted:
       # print "ballots generated with multiplicities:"
        #for b in sorted(d.keys()):
        #    print b, d[b]
       # print

##############################################################################
## generate profile of size n of ballots that is similar in terms of
## preferences to a given sample B of ballots
##############################################################################

def sample(B, n, printing_wanted=True):
    """ 
    Input: B is list of ballots (over candidates range(m)).
           n is desired number of ballots to generate and return.
    Output: list S of n ballots that are "like" those in B,
            in the sense that matrix of prefs for S is close to 
            (percentage-wise) those in B. 
            (Some variations on prefs are deliberately added for variability.)

    Notes: Procedure is randomized; likely to return different S each time.
           Preference matrix for B is used as template, but:
              scaled up so for each i,j:  A[i,j]+A[j,i] = n
              Given preferences A[i,j],A[j,i] only used a parameters for
                 a beta distribution to determine final A[i,j],A[j,i]
           Tideman's ranked-pairs method used repeatedly to construct a
           a ballot that best fits remaining marginals, until you have n ballots.
    """

    if printing_wanted:
        print "number of ballots desired = ", n
        print "Profile of ballots provided:"
        for ballot in B:
            print ballot

    A = prefs(B)
    generate_tweaked_profile(A, n)

def test_sample():
    sample(B1, 100)
    sample(B2, 100)
    sample(B3, 100)
    sample(B4, 100)

test_sample()

##############################################################################
## end of profile-generating code
##############################################################################

    
    





# "rivest" subdirectory of 2016-aus-senate-audit

This is a place for Ron Rivest to store some local files of possible interest.

Current contents:

``sp2.py``              Slightly modified copy of original "variant sample" routine of Rivest and Yu.
                        This is probably not going to be used, as it is rather slow.
                        We'll use the Bayesian method instead.

``git-notes.org``       Notes on using ``git``.

``xz-notes.org``        Notes on using compression scheme ``xz``

``api.py``              Draft of possible API interfacting dividebatur with aus.py

``api_dividebatur.py``  API for interface with dividebatur submodule for doing vote-counting.

``audit_tie_breaker.py``  Routine to break ties during audit in a way consistent with how they were broken during official tally.

``aus.py``              Initial draft of Bayesian audit framework.

``aus2.py``             Revision of aus.py to use ``api.py``; also much more efficient since it uses ballot weights and gamma variates.

``sampler.py``          Routine for performing random sample of a set of ballots. (Needs modifications for use here.)





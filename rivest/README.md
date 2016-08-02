# "rivest" subdirectory of 2016-aus-senate-audit

This is a place for Ron Rivest to store some local files of possible interest.

Current contents:

``sp2.py``              slightly modified copy of original "variant sample" routine of Rivest and Yu.
                        This is probably not going to be used, as it is rather slow.
                        We'll use the Bayesian method instead.

``git-notes.org``       Notes on using ``git``.

``xz-notes.org``        Notes on using compression scheme ``xz``

``api.py``              Draft of possible API interfacting dividebatur with aus.py

``api_dividebatur.py``  Implements an API based on ``api.py`` for interfacing with dividebatur.

``aus.py``              Initial draft of Bayesian audit framework.

``aus2.py``             Revision of aus.py to use ``api.py``; also much more efficient since it uses ballot weights and gamma variates.





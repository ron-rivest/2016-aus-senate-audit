# 2016-aus-senate-audit

This repository supports the possible auditing of the 2016 Australian
Senate elections.

This work is joint with Vanessa Teague (U. Melbourne), Philip Stark (UC Berkeley),
Zara Perumal (MIT), Ian Gordon (U. Melbourne), Damjan Vukcevic, and
Ronald L. Rivest (MIT).

One approach explored here is to use "black-box auditing" methods
developed by Stark and Rivest (unpublished, although mentioned in
[this talk](http://people.csail.mit.edu/rivest/pubs.html#Riv16x)).
These are ballot-polling methods (not comparison audits).  This
approach also uses methods developed by Rivest and Yu for computing a
"variant sample" of a set of ranked-choice ballots.

Another approach we expect to explore is the 
["Bayesian audit"](http://people.csail.mit.edu/rivest/pubs.html#RS12)
method of Rivest and Shen.

We use with appreciation python [code and
materials](https://github.com/grahame/dividebatur) developed by
Grahame Bowland for computing the outcome of such an election,
as well as
[code and materials](https://github.com/berjc/election-engine)
developed by Berj K Chilingirian, Zara Perumal, and Eric C Huppert as a framework for election auditing.

This work is all in python, and requires python 3.

Further materials related to post-election audits can be found on the
[voting-related web page of Philip B. Stark](https://www.stat.berkeley.edu/~stark/Vote/index.htm).




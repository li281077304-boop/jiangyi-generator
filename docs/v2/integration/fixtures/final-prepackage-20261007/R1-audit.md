# R1 audit status: failed candidates, no retained rule

Two read-only source pairs were audited. X019/X020 Q21 has identical student/teacher source stem and options at physical starts b183/b380; both were absent from A-Line occurrence output. The diagnostic helper recovered those starts, but full alignment then found 28 student occurrences versus 27 teacher occurrences, so that topic did not pass.

X001/X002 includes numbered knowledge-list text under a knowledge section; it must remain outside question identity. R1-A's broader raw-start recovery promoted similar knowledge content in X12.4 and caused a baseline PASS regression. R1-B's knowledge filter did not recover any new PASS.

R1-A result: 1/33, 0 new PASS, 1 lost baseline PASS. R1-B result: 0/33, 0 new PASS, 2 lost baseline PASS. Neither candidate is retained; source and test files were restored to base HEAD. See `R1-review.md` and `R1-B-outcome.json` for the complete failure review and hashes.

# Milestone2
the Milestone 2 takes a relational algebra query, which is the output of Milestone 1 
(translation of SQL into relational algebra.) <br> and apply on it some rules for the logical 
optimization of relational algebra query.<br>


![ScreenShot](https://github.com/KacemHamza97/Milestone2/blob/main/images/optimization_rules.png)


Rule 1: states that a conjunction in a selection predicate may be broken into several
nested selections. At the same time, nested selections may be merged into a single
selection with a conjunctive predicate. <br>

Rule 2: states that nested selections may swap places. <br>

Rule 3: states that a selection can be pushed down over a cross product, if it only
requires the attributes of one of the operands. In the rule as stated above, we as-
sume that predicate p only requires attributes from R 1 . (We need to consult the data
dictionary recording the name and attributes of each relation). <br>

Rule 4: describes how a selection and a cross product may be merged into a theta
join, provided that the selection predicate is a join condition. This is the case if it
compares attributes of R 1 and R 2 . <br>
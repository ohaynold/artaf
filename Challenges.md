# Challenges

- Neal anticipates challenges with the statistical analysis of the data, as he didn't ever get past rudimentary statistics classes. He also is thinking about resource management with large quantities of data that we will be processing: we might have to use some resource management libraries if it looks like our dataset is exceedingly large -- technical challenges.
- Oliver feels confident about these things -- difference in comfort level.
- Neal and Oliver work in very different time zones and work schedules, necessitating mostly asynchronous collaboration -- logistical challenge.

## Progress on Challenges

We have made an initial sprint pushing to remove risks from the project, *viz.* that anything might go wrong with
data acquisition. The project is now in a condition where it can download the full dataset starting in 2010 from Iowa
State's collection and parse the TAFs with a very low failure rate and the failing TAFs indeed looking like encoding or
transmission errors that should fail. Thus, the dataset is in hand now, and we are on a predictable course to
producing code for the analysis itself.

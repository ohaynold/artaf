For now, this is just same sample analysis as a framework.

# Some Summary Statistics

We have loaded 139376801 data lines for 713 aerodromes for configuration
full_set.

## Distribution of Wind Speeds

![](Statistics_files/figure-markdown_github/unnamed-chunk-2-1.png)

![](Statistics_files/figure-markdown_github/unnamed-chunk-3-1.png)

# Autocorrelations

Now to the interesting part, the autocorrelations.

## Wind speed

We’ll start with looking at changes in wind speed from the previous to
the current TAF as predictors of wind speed in the final TAF reported
for a given hour. The data are filtered to cases where the wind speed in
the previous TAF, the current TAF as well as the final TAF did not
exceed 30 knots so as to filter out cases of extreme weather and
transmission errors, which may be hard to distinguish.

![](Statistics_files/figure-markdown_github/unnamed-chunk-4-1.png)

We notice a distinctive asymmetry in this plot. Whereas for reductions
in predicted wind speed, we hardly see much predictive value, increases
in predicted wind speed seem to be overly aggressive in the sense of the
predictions not usually coming true.

It seems that for increases in predicted wind speed of 25 knots or more,
we can back these out entirely, so these may reflect transmission
errors. For smaller increases, however, we can back out about a third of
the increase for the median, with about equal changes that we can beack
out the entire change or that the change will come substantially true.

Repeating the analysis by year, we see that the pattern appears largely
unchanged.

![](Statistics_files/figure-markdown_github/unnamed-chunk-5-1.png)

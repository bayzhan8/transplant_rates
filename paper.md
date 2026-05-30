---
title: 'Transplant Rates: a Python package for comparing kidney allocation policies from simulation outputs'
tags:
  - Python
  - organ transplantation
  - kidney allocation
  - health policy
  - simulation
  - SRTR
authors:
  - name: Bayzhan Mukatay
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Daniyar Akhizhanov
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Sommer E. Gentry
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: Center for Surgical and Transplant Applied Research, NYU Grossman School of Medicine, New York, NY, USA
    index: 1
date: 30 May 2026
bibliography: paper.bib
---

# Summary

`transplant_rates` is a Python package for comparing candidate kidney allocation
policies. It takes the output of an organ allocation simulator (for example, OASim)
together with registry data from the Scientific Registry of Transplant Recipients
(SRTR) and measures how often candidates in different groups receive a transplant.

A simulator records which donor kidneys were placed with which waitlisted
candidates. From that record, the package reconstructs how long each candidate spent
on the waitlist during the simulation, counts the transplants in each group, and
reports transplant rates per patient-year. Rates can be split by candidate age, race,
ethnicity, sex, blood type, Estimated Post-Transplant Survival (EPTS), and Calculated
Panel Reactive Antibody (CPRA). A second class, `OffersCalculator`, works with
individual organ offers instead of completed transplants: how many offers each kidney
generated, and how donor quality (measured by KDPI) varied with recipient EPTS, race,
and time waited. The package also builds the summary tables and figures used to
present these comparisons.

So that the code can be run without access to restricted registry data, the
repository includes a generator that produces a small synthetic dataset and a
notebook that runs the full analysis on it.

# Statement of need

Changes to kidney allocation rules affect which patients are transplanted, so
proposed rules are often tested with allocation simulators before they are adopted.
These simulators produce large files that list, for each simulated transplant, the
donor and the candidate who received the organ. Turning those files into the numbers
that policy discussions rely on (transplant rates within subgroups, the waitlist time
those rates are divided by, and comparisons between competing policies) takes a fair
amount of bookkeeping, and the same code tends to be rewritten for each new project.

Two parts of that bookkeeping are easy to get wrong. The first is the denominator:
waitlist time has to be cut off at the right moment, whether that is a transplant, a
removal, a relisting, or the end of the simulation window, or the rates come out
wrong. The second is assigning time-varying values such as EPTS and CPRA as they
stood at the start of the simulation rather than at some later date.

`transplant_rates` keeps this work in one place. One goal of the package is to give a
standard, reusable way to compute transplant rates across demographic groups and to
analyze and compare OASim outputs, instead of rewriting one-off code for each study.
It handles the joins between the simulator output and the registry tables, computes
waitlist person-time, and applies one rate definition (transplants per patient-year)
behind a small set of functions.
Comparing several policies, including repeated stochastic runs of the same policy
reported as mean, minimum, and maximum, takes only a few lines of code.
`OffersCalculator` reuses the same data handling to answer offer-level questions
about allocation efficiency and donor quality.

The package is intended for transplant researchers and analysts who need repeatable
subgroup comparisons, and for people developing allocation simulators. We have used
it for allocation analyses within our own group. Because the registry data cannot be
shared, the package ships with a synthetic data generator, which lets others run the
full workflow and lets the test suite run without protected data.

# State of the field

Allocation simulators such as the SRTR Simulated Allocation Models [@SRTR_SAM] and
OASim generate the event-level outputs that this package consumes, but they stop at
the allocation step: they record which donor organs were placed with which
candidates and do not compute subgroup transplant rates, the waitlist person-time
those rates are divided by, or comparisons across policies. General-purpose survival
and rate libraries, such as `lifelines` [@DavidsonPilon2019lifelines] in Python or
the `survival` package in R, can estimate rates once a clean analytic table exists,
but they are not aware of the structure of allocation-simulator output and do not
perform the simulator-specific work that precedes a rate calculation: joining
allocation events to registry tables, censoring waitlist time at transplant,
removal, relisting, or the end of the simulation window, and snapshotting
time-varying covariates such as EPTS and CPRA at the start of the simulation.

We are not aware of an openly available package that fills this gap, so analysts
typically rewrite one-off scripts for each study. We built `transplant_rates` rather
than extending an existing tool because the work that distinguishes a correct
analysis here is domain-specific: the censoring rules for the person-time
denominator, the time-of-listing snapshot of allocation covariates, and the
aggregation of repeated stochastic simulation runs into mean, minimum, and maximum
rates. These concerns sit upstream of the generic rate computation that existing
libraries already handle well, and the package is designed so that the rate
definition and the offer-level analysis can be reused and extended across studies.

# Research impact

`transplant_rates` is used within our group as the standard tool for turning
allocation-simulation output into policy comparisons. Several analyses built with it
have been accepted for presentation at the American Transplant Congress (ATC), and
additional projects that depend on it are in progress.
<!-- TODO: add citations/DOIs for the specific ATC abstracts once available. -->
To make the workflow reproducible without access to restricted registry data, the
repository ships a synthetic data generator and a quick-start notebook that run the
full pipeline end to end, and an automated test suite that exercises the rate and
offer calculations on that synthetic data.

# AI usage disclosure

Generative AI coding assistance (the Cursor editor) was used while preparing this
release to help with code refactoring, documentation, the test suite, the synthetic
data generator, and the drafting of this paper. The statistical definitions, the
censoring and person-time logic, the design of the package, and the interpretation of
results were determined by the authors. All AI-assisted code and text were reviewed by
the authors, and the analysis code is covered by the automated tests described above.

# Acknowledgements

We thank colleagues at the Center for Surgical and Transplant Applied Research for
their feedback on the analysis pipeline. The data reported here have been supplied by
the SRTR. The interpretation and reporting of these data are the responsibility of
the authors and do not represent official policy of the SRTR or the U.S. Government.

# References

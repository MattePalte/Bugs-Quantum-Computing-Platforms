# Bugs in Quantum Computing Platforms: An Empirical Study
Companion Repository for ["Bugs in Quantum Computing Platforms: An Empirical Study"](https://arxiv.org/abs/2110.14560)

In the `artifacts` folder you can find the following resources:
1. **commits_considered_for_sampling.csv**: containing the full list of commits considered for sampling, namely all the pairs of repository name and
commit hash.
2. **annotation_bugs.csv**: including all the annotated commits which resulted either in bugs or false positives. For the bugs we further annotate bug type, components, symptom, and bug patterns. To describe the bug, we also have a comment column which contains a brief natural language description or a quote from a developer involved in the discussion of such bug. Moreover, we also have a link which aims at roughly identifying the location of the bug in the commit or pointing to some relevant resource to understand the bug.
3. **annotation components.csv**: containing information on which part of the repository lead us to the decision that a specific project include a specific component, e.g., quantum abstraction or machine code generation. We report this for each platform together with the reference to the commit we used during inspection.

## Update
Note that the repository of the platform named `tequila` has been moved from `https://github.com/aspuru-guzik-group/tequila`, which you find in our data artifacts, to `https://github.com/tequilahub/tequila`, which is the new location.
Please use the correct path to avoid 404 error.

We also encourage and thank in advance anyone who informs us in case this happens with another platform.


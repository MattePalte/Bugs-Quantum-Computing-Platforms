To minimize the Bugs

we apply the following steps:
- remove from the diff:
    - empty lines from the newly added code
    - Comments
    - new test added as regression test which should prevent the same bug to reappear
- if the change is semantically equivalent, namely old and new versions are semantically equivalent, then the old version is propagated in the new version.

Note that when a new method method is replaced with two methods then we delete the docstrings to avoid matches on the comments.

We annotate if the same change is repeated in multiple position

In case we have a change which is not relevant we keep the **before version**, namely we propagate the change from before to after, left to right.

If the change is from a JSON file derived from the code, such as a mock for test, we ignore it.

## Diff Counting Algorithm

Iterate over the files of the folder `before` and `after` and count the number of changes.

We do not count a file if it is:
- empty
- identical before and after


## Data Collection of Modified Commits

1. We download the repos locally
1. we use pydriller to save all the modified files before and after the commit
    - **Exception**: when the commit has more than one parent the list of modified files is empty (this should be noticed easily since the folder of a commit should not be empty)


## Exceptions

- Qiskit-terra#891 refers to Qiskit/qiskit-aqua#891
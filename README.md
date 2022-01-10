# Bugs in Quantum Computing Platforms: An Empirical Study
Companion Repository for ["Bugs in Quantum Computing Platforms: An Empirical Study"](https://arxiv.org/abs/2110.14560)

## Reusing this Research

This publication can be reused in at least two ways:
- **Bug Collection**: we provide a dataset of bugs that have been minimized accounting only the files and lines of code which were responsible for the bug fix. This can be manually inspected to get deeper insights on the types of bugs that occurs in quantum computing platforms. Each bug fix contains two subfolders, named `before` and `after`, with the files before and after the fix. We recommend using a visual tool like [*Meld*](https://meldmerge.org/) to compare the files before and after the bugfix.
    **Target audience**: researchers interested in inspecting bug patterns of quantum computing platforms in details.

- **Bug Study**: we provide the code to conduct our empirical study on the annotated data.  The code to produce the diagrams can be reused to compute these metrics for any other annotated bug datasets (e.g., in another context or for an extension of the current work).
    **Target audience**: researchers conducting an empirical study of bugs.


**Potential Ideas for Future Work**:
1. **Extension for APR**: The bug collection dataset could be augmented with bug-triggering test cases to create a quantum specific benchmark for automatic program repair (APR) techniques.
1. **Extension for Code Evolution Study**: in some time, the current bug collection dataset could be extended with future bugfixes to investigate how the studied metrics has changed over time in the quantum computing platforms.


## Available Artifacts

This repository contains the following resources.

1. **commits_considered_for_sampling.csv**: containing the full list of commits considered for sampling, namely all the pairs of repository name and
commit hash. Resource path: [artifacts/commits_considered_for_sampling.csv](artifacts/commits_considered_for_sampling.csv).
2. **annotation_bugs.csv**: including all the annotated commits which resulted either in bugs or false positives. For the bugs, we further annotate `bug type`, `components`, `symptom`, and `bug patterns`. To describe the bug, we also have a `comment` column which contains a brief description of the bug or a quote from a developer involved in the discussion of such bug. Moreover, we also have a column `localization` which contains a link that roughly identifies the location of the bug in the commit or pointing to some relevant resource to understand the bug. Resource path: [artifacts/annotation_bugs.csv](artifacts/annotation_bugs.csv).
3. **annotation_components.csv**: containing information on which part of the repository led us to the decision that a specific project includes a specific component, e.g., quantum abstraction or machine code generation. We report this for each platform together with the reference to the commit we used during manual source code inspection. Resource path: [artifacts/annotation_components.csv](artifacts/annotation_components.csv).
4. **minimal_bugfixes** folder: containing the minimal bugfixes that are required to fix the annotated bugs. Resource path: [artifacts/minimal_bugfixes/](artifacts/minimal_bugfixes/). The bugfixes are grouped per repository, and each bugfix folder contains two subfolders, named `before` and `after`, which contain the relevant files before and after the bugfix.
5. **Reproducibility_of_Paper_Analysis.ipynb**: containing the steps to reproduce the diagrams in the paper. Resource path: [notebooks/Reproducibility_of_Paper_Analysis.ipynb](notebooks/Reproducibility_of_Paper_Analysis.ipynb).


The bugs have two unique ids for historical reasons, but a single id is enough to unequivocally identify a bug.
The two ids are named:
- `id`: which is an incremental number used to uniquely identify the bug, it was used during the annotation process, and if the same commit contains multiple bug fixes, we use a decimal number to refer to the additional bugs (e.g., given the commit `acb123`, first bug has id of `75`, whereas the second has `75,5` ).
- `human_id`: which was introduced for readability purposes. It is a derived id s which is a combination of repository name followed by the first issue mentioned in the commit message, such as `pennylane#481`. In case of multiple bugs in the same commit we use the naming convention: `pennylane#481` and `pennylane#481_B`.

Note that we never have more than two bugs per commit in this dataset.


## Reproducibility of Paper Analysis

The notebook [Reproducibility_of_Paper_Analysis.ipynb](notebooks/Reproducibility_of_Paper_Analysis.ipynb) contains all the required steps to reproduce all the main paper's results in terms of diagrams and tables.

**Hardware and Software Setup**

We test the analysis on the following setup:
- Operating System: Ubuntu 20.04.3 LTS
- Kernel: Linux 5.4.0-91-generic
- Architecture: x86-64
- CPU: Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz
- conda 4.10.1
- Python 3.8.0
- RAM: 32 GB

**Step-by-Step Reproducibility**

Follow these steps to reproduce the paper's results. You can either use the docker container or set up the conda environment.

**OPTION A - Docker Container Approach**
1. Go in the main directory of this repo
2. Run the following command to download and run the docker container with all the dependencies of the notebook:
```bash
docker run -i -p 8888:8888 -v "$(pwd)":/home/jovyan -t jupyter/datascience-notebook:ubuntu-20.04 /bin/bash
```

**OPTION B - Conda Environment Approach**

1. To use the notebook with the exact dependencies we used, you have to create the same conda environment starting from the environment file named [conda_environment.yml](conda_environment.yml) in the root of the repository. Run the following command to set up your environment:
    ```bash
    conda env create --file conda_environment.yml
    ```
    Note that your system might have assigned a different name to the environment, thus use the one mentioned in your printout at the line `conda activate **environment_name**`. Make sure to use the right one, the default name should be `QuantumPlatformBugs`, but the name is an irrelevant detail.
2. Then activate the conda environment by running:
    ```bash
    conda activate QuantumPlatformBugs
    ```
    make sure that the name of your environment is visible in the command line.
    ```bash
    (QuantumPlatformBugs) matteo@ubuntu:~/.../Bugs-Quantum-Computing-Platforms/
    ```
**Common Step for Analysis**

3. Now run the jupyter notebook kernel:
    ```bash
    jupyter notebook
    ```
4. From the web UI, navigate to the `notebooks` directory, open and run top to bottom the [Reproducibility_of_Paper_Analysis.ipynb](notebooks/Reproducibility_of_Paper_Analysis.ipynb) notebook.
Note that the notebook will output images which will be saved in the folder: [reproducibility_results](reproducibility_results).





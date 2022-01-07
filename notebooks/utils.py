import pandas as pd
import numpy as np
from typing import Union
from typing import List
from typing import Tuple
from typing import Dict
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import os


# UTILITY FUNCTIONS: DATA INGESTION AND MANIPULATION


def read_bugs(filepath: str) -> pd.DataFrame:
    """Read the bugs from the CSV file."""
    data = pd.read_csv(filepath)
    df_bugs = data[data['real'] == 'bug']
    df_bugs = df_bugs.replace(
        {"type": {
            "classical": "Classical",
            "quantum": "Quantum"
        }})
    return df_bugs


def read_google_sheet_dump(filepath):
    """Read the dump from Google Sheet."""
    data = pd.read_csv(filepath, header=2)
    data = data[[
        'repo', 'commit_hash', 'real', 'type',
        'component', 'symptom', 'bug_pattern', 'id', 'complexity'
    ]]
    df_bugs = data[data['real'] == 'bug']
    df_bugs = df_bugs.replace(
        {"type": {
            "classical": "Classical",
            "quantum": "Quantum"
        }})
    return data, df_bugs


def expand_columns(
        df: pd.DataFrame,
        col_to_expand: Union[str, List[str]]
        ) -> pd.DataFrame:
    """Expand row, one for each comma separated value in col_to_expand.

    This is used to expand when multiple labels are present on the same bug.
    """
    records = df.to_dict('records')

    initial_n_records = len(records)
    if not isinstance(col_to_expand, list):
        col_to_expand = [col_to_expand]
    for col in col_to_expand:
        new_records = []
        for r in records:
            try:
                assert isinstance(r[col], str)
            except AssertionError:
                print(r)
            for token in r[col].split(","):
                new_r = dict(r)
                new_r[col] = token.strip()
                new_records.append(new_r)
        records = new_records
    n_annotations = len(records)
    print(
        f"{initial_n_records} records received {n_annotations} annotations"
        f" in the column(s): {col_to_expand}."
    )
    return df.from_dict(records)


def normalize_complexity(df: pd.DataFrame, verbose: bool) -> pd.DataFrame:
    """Regularize the complexity column between 0 to 20."""
    before = len(df)
    df["complexity"] = df["complexity"].apply(
        lambda e: "100" if e == "100+" else e
    )
    df.dropna(subset=['complexity'], inplace=True)
    df["complexity"] = df["complexity"].astype(int)
    after = len(df)
    if verbose:
        print(f"Complexity normalization: {before} (before) > {after} (after)")
    return df


def cap_max_value(df: pd.DataFrame, column_to_inspect: str, max_value: int):
    """Cap the maximum value of the column."""
    df[column_to_inspect] = df[column_to_inspect].apply(
        lambda e: max_value if e > max_value else e
    )
    return df


def capitalize(string: str) -> str:
    if len(string) > 1:
        return string[0].upper() + string[1:]
    return string.upper()


# PLOTTING FUNCTIONS


def plot_bar_chart_quantum_vs_classical(
            df_bugs: pd.DataFrame,
            column_to_inspect: str,
            mapping_dict: Dict[str, str],
            categories_to_exclude: List[str] = [],
            categories_keep_only: List[str] = None,
            out_file_name: str = None,
            out_folder_path: str = None,
            horizontal: bool = False,
            map_value_since_beginning: bool = False,
            figsize: Tuple[int, int] = (10, 5),
            legend_placement: str = 'upper center'
        ):
    """Plot a bar chart with quantum and classical column for each category."""

    fig, ax = plt.subplots(figsize=figsize)

    df = expand_columns(df_bugs, column_to_inspect)
    df = df[~(df[column_to_inspect].isin(categories_to_exclude))]

    if categories_keep_only is not None:
        df = df[df[column_to_inspect].isin(categories_keep_only)]

    if map_value_since_beginning:
        df[column_to_inspect] = df[column_to_inspect].map(mapping_dict)

    categories_q_bugs = list(df[
        df['type'] == 'Quantum'].groupby(
        column_to_inspect).count().sort_values(
        by='type', ascending=False).index)

    for component in df[column_to_inspect].unique():
        if component not in categories_q_bugs:
            categories_q_bugs.append(component)

    args = {
        "hue": "type",
        "data": df,
        "palette": PALETTE,
        "ax": ax,
        "order": categories_q_bugs
    }

    if horizontal:
        sns.countplot(y=column_to_inspect, **args)
        ax.grid(axis='x')
    else:
        sns.countplot(x=column_to_inspect, **args)
        ax.grid(axis='y')

    if not map_value_since_beginning:
        # map the value at the latest stage, thus in the labels
        obj_labels = ax.get_xticklabels()
        for i, l in enumerate(obj_labels):
            obj_labels[i] = mapping_dict[l.get_text()]
        ax.set_xticklabels(obj_labels, rotation=60, ha='right')

    ax.set_xlabel(capitalize(column_to_inspect), fontsize=15)
    ax.set_ylabel("Count", fontsize=15)
    plt.legend(title="Type of Bug", loc=legend_placement)
    plt.tight_layout()

    if out_file_name is not None and out_folder_path is not None:
        fig.savefig(os.path.join(out_folder_path, out_file_name), format="pdf")


def plot_histogram_quantum_vs_classical(
            df_bugs: pd.DataFrame,
            column_to_inspect: str,
            cap_value: int = 20,
            out_file_name: str = None,
            out_folder_path: str = None,
            column_label_name: str = None,
            column_abbreviation: str = None,
            figsize: Tuple[int, int] = (10, 5),
            legend_placement: str = 'upper center',
            median_heights: Tuple[int, int] = (41, 41),
            median_shifts: Tuple[int, int] = (.75, .75),
            median_on: bool = True
        ):
    """Plot a stacked histogram (quantum vs classical) for the given metric."""
    df = df_bugs
    # df = normalize_complexity(df, verbose=True)
    df = cap_max_value(df, column_to_inspect, cap_value)
    if column_label_name is None:
        column_label_name = column_to_inspect
    if column_abbreviation is None:
        column_abbreviation = column_label_name
    max_val = cap_value + 2
    fig, ax = plt.subplots(figsize=figsize)

    mpl.rcParams['legend.loc'] = legend_placement
    sns.histplot(
        data=df,
        hue='type',
        multiple='stack',
        palette=PALETTE,
        x=column_to_inspect,
        bins=range(max_val),
        ax=ax
    )
    mpl.rcParams['legend.loc'] = 'best'
    ax.get_legend().set_title(title="Type of Bug")
    ax.set_xticks(np.arange(.5, max_val, 1))
    new_labels = [
        str(e) if e != max_val - 1 and e != 0 else ""
        for e in range(max_val)
    ]
    new_labels[cap_value] = f"{cap_value}+"
    # print(new_labels)
    ax.set_xticklabels(new_labels)
    if median_on:
        # MEDIAN VALUE - QUANTUM
        median_quantum = df[
            df['type'] == 'Quantum'][column_to_inspect].median()
        ax.axvline(x=.5 + median_quantum, color=PALETTE["Quantum"])
        ax.text(
            median_quantum + median_shifts[0], median_heights[0],
            f'Median {column_abbreviation}\nfor " \
            "Quantum\nBug-fixes ({median_quantum})',
            fontsize=12, color=PALETTE["Quantum"])
        # MEDIAN VALUE - CLASSICAL
        median_classical = df[
            df['type'] == 'Classical'][column_to_inspect].median()
        ax.axvline(x=.5 + median_classical, color=PALETTE["Classical"])
        ax.text(
            median_classical + median_shifts[1], median_heights[1],
            f'Median {column_abbreviation}\nfor " \
            "Classical\nBug-fixes ({median_classical})',
            fontsize=12, color=PALETTE["Classical"])
    ax.set_xlabel(f"{column_label_name} ({column_abbreviation})", fontsize=15)
    ax.set_ylabel("Count", fontsize=15)
    ax.set_xlim(1, cap_value + 1)
    plt.tight_layout()
    ax.grid(axis='y')
    # fig.set_dpi(300)
    if out_folder_path is not None and out_file_name is not None:
        fig.savefig(os.path.join(out_folder_path, out_file_name), format="pdf")


def plot_diagram_value(
            df_bugs: pd.DataFrame,
            column_to_inspect: str,
            exclude_values: List[str] = [],
            mapping_latex: Dict[str, str] = None,
            latex_format: bool = False
        ):
    """Print the values for the diagram."""
    df = expand_columns(df_bugs, column_to_inspect)
    records = []
    for col_value in list(df[column_to_inspect].unique()):
        count = len(df[df[column_to_inspect] == col_value])
        if latex_format and mapping_latex is not None:
            col_value = mapping_latex[col_value]
        records.append(
            {"code": col_value, "count": count}
        )
    df_agg = pd.DataFrame.from_records(records)
    df_agg = df_agg.groupby("code").sum().reset_index()
    print("-" * 80)
    for i, row in df_agg.iterrows():
        code = str(row['code'])
        count = str(row['count'])
        if code not in exclude_values:
            if latex_format:
                print(
                    "\\node[above right=-.5em and -1.5em of " + code +
                    "] {" + count + "};"
                )
            else:
                print(f"'{code}' was annotated {count} time(s).")
    print("-" * 80)


# CONSTANTS


PALETTE = {
    'Quantum': sns.color_palette("tab10")[1],
    'Classical': sns.color_palette("tab10")[0]
}

ALIAS_COMPONENTS_SHORT = {
    "Classical Abstractions": "Classical\nAbstractions",
    "Domain-specific Abstractions": "Domain-specific\nAbstractions",
    "Infrastructural Scripts and Glue Code": "Scripts and\nGlue Code",
    "Interface to Quantum Computer": "Interface to\nQuantum Computer",
    "Intermediate Representation": "Intermediate\nRepresentation",
    "Machine Code Generation": "Machine Code\nGeneration",
    "Optimizations": "Optimizations",
    "Quantum Abstractions": "Quantum\nAbstractions",
    "Quantum State Evaluation": "Quantum State\nEvaluation",
    "Simulator": "Simulator",
    "Testing": "Testing",
    "Tutorial and Examples": "Tutorial and\nExamples",
    "Visualization and Plotting": "Visualization\nand Plotting",
}
ALIAS_SYMPTOMS_SHORT = {
    "Compilation Error": "Compilation\nError",
    "Crash": "Crash",
    "Crash - Application Error": "Crash\nApp Error",
    "Crash - OS/PL Error": "Crash\nOS/PL Error",
    "Failing Test": "Failing\nTest",
    "Incorrect Final Measurement": "Incorrect Final\nMeasurement",
    "Incorrect Output": "Incorrect\nOutput",
    "Incorrect Visualization": "Incorrect\nVisualization",
    "Inefficiency": "Inefficiency",
    "Non-termination": "Non-termination",
    "Other Non-functional": "Other\nNon-functional",
    "Unclear": "Unclear",
}

# HIERARCHY COUNT

ALIAS_FOR_HIERARCHY_OF_SYMPTOMS = {
    "Compilation Error": "compil",
    "Crash": "crash",
    "Crash - Application Error": "crashApp",
    "Crash - OS/PL Error": "crashOS",
    "Inefficiency": "ineff",
    "Failing Test": "test",
    "Incorrect Final Measurement": "incorMeas",
    "Incorrect Output": "incorOut",
    "Non-termination": "notTerm",
    "Other Non-functional": "other",
    "Incorrect Visualization": "incorViz",
    "Unclear": "unclear",
}

# to match the names in the paper
ALIAS_BUG_PATTERN_SHORT = {
    "API Misuse - External": "API misuse",
    "API Misuse - Internal": "API misuse",
    "API Outdated - External": "Outdated API client",
    "API Outdated - Internal": "Outdated API client",
    "Wrong Concept": "Wrong concept",
    "Incorrect IR - Missing Information": "Incorrect IR - Missing information",
    "Incorrect IR - Wrong Information": "Incorrect IR - Wrong information",
    "Incorrect Numerical Computation": "Incorrect numerical computation",
    "Incorrect Randomenss Handling": "Incorrect randomenss handling",
    "Incorrect Scheduling": "Incorrect scheduling",
    "MSB-LSB convention mismatches": "MSB-LSB convention mismatch",
    "Overlooked Corner Case": "Overlooked corner case",
    "Overlooked Qubit Order": "Incorrect qubit count",
    "Qubit Count Related": "Incorrect qubit order",
    "Wrong Identifier": "Wrong identifier",
    "String Bug": "Incorrect string",
    "Flaky Test": "Flaky test",
    "GPU related": "GPU related",
    "Memory Leak": "Memory leak",
    "Misconfiguration": "Misconfiguration",
    "Type Problem": "Type problem",
    "Typo": "Typo"
}

ALIAS_FOR_HIERARCHY_OF_BUG_PATTERNS = {
    "API Misuse - External": "apiMisuse",
    "API Misuse - Internal": "apiMisuse",
    "API Outdated - External": "apiOutdated",
    "API Outdated - Internal": "apiOutdated",
    # "Barrier Related": "barrier",
    # "Chain Strength": "chain",
    "Wrong Concept": "cptSwap",
    # "Concurrency": "concur",
    # "Conflicting Statements": "confStmt",
    # "Flaky Test": "flakyTest",
    # "GPU related": "gpu",
    # "Imprecise Result": "imprResult",
    # "Incorrect Circuit": "incCirc",
    "Incorrect IR - Missing Information": "irMiss",
    "Incorrect IR - Wrong Information": "irWrong",
    "Incorrect Numerical Computation": "numComp",
    "Incorrect Randomenss Handling": "incRand",
    # "Incorrect Resources Access": "incResource",
    "Incorrect Scheduling": "incSched",
    "MSB-LSB convention mismatches": "msbLsb",
    # "Memory Leak": "memLeak",
    # "Misconfiguration": "misconf",
    # "Missing Error Handling": "missErr",
    # "Missing Implementation": "missImpl",
    # "Numerical Error": "numErr",
    "Overlooked Corner Case": "ovCorn",
    "Overlooked Qubit Order": "QuOrder",
    "Qubit Count Related": "QuCount",
    "String Bug": "string",
    # "String Encoding Related": "str",
    # "Syntax Error": "syntax",
    # "Type Problem": "type",
    # "Typo": "typo",
    "Wrong Identifier": "wrongId",
    # "Wrong Static Mapping": "wrongMap",
    "Flaky Test": "flakyTest",
    "GPU related": "gpu",
    "Memory Leak": "memLeak",
    "Misconfiguration": "misconf",
    "Type Problem": "type",
    "Typo": "typo",
}

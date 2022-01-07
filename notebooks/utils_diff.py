"""Utils to compute the diff from the minimized bugs."""

import os
import difflib as dl
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
from typing import List


def read_content(path):
    """Read the content of a file."""
    with open(path, 'r') as in_file:
        return in_file.read()


def iterate_over(folder_master, folder_slave):
    """Iterate over file with the two folders, return the file contents.

    Note that only files in common are returned.
    """
    files_in_master = [
        f for f in os.listdir(folder_master)
        if os.path.isfile(os.path.join(folder_master, f))
    ]
    files_in_slave = [
        f for f in os.listdir(folder_slave)
        if os.path.isfile(os.path.join(folder_slave, f))
    ]
    files_in_common = set(files_in_master).intersection(set(files_in_slave))
    results = []

    for filename in files_in_common:
        file_master = os.path.join(folder_master, filename)
        file_slave = os.path.join(folder_slave, filename)
        # print(file_master)
        # print(file_slave)
        content_master = read_content(file_master)
        content_slave = read_content(file_slave)
        item = (filename, content_master, content_slave)
        results.append(item)
    return results


def get_line_numbers(line):
    token = line.split(" ")
    numbers_old_file = token[1]
    numbers_new_file = token[2]
    delete_line_number = (
        int(numbers_old_file.split(",")[0].replace("-", "")) - 1
    )
    additions_line_number = int(numbers_new_file.split(",")[0]) - 1
    return delete_line_number, additions_line_number


def get_hunks(text_diff):
    """Extract the hunks form the unified diff."""
    lines = text_diff.split("\n")
    modified_lines = {
        "added": [],
        "deleted": [],
    }

    count_deletions = 0
    count_additions = 0

    chunks = []

    # there are different section types:
    # header, unchanged_text, add_section, del_section
    c_section = 'unchanged_text'
    prev_section = 'unchanged_text'
    chunk = {
        "added": [],
        "deleted": [],
    }

    for line in lines:
        line = line.rstrip()
        count_deletions += 1
        count_additions += 1

        if line.startswith("@@"):
            c_section = 'header'
            count_deletions, count_additions = get_line_numbers(line)
            # initialize a new dictionary for the change hunk
            chunk = {
                "added": [],
                "deleted": [],
            }

        elif line.startswith("-"):
            c_section = 'del_section'
            modified_lines["deleted"].append((count_deletions, line[1:]))
            count_additions -= 1
            # append this line as deleted line of this change hunk
            chunk["deleted"].append((count_deletions, line[1:]))

        elif line.startswith("+"):
            c_section = 'add_section'
            modified_lines["added"].append((count_additions, line[1:]))
            count_deletions -= 1
            # append this line as added line of this change hunk
            chunk["added"].append((count_additions, line[1:]))

        elif line == r"\ No newline at end of file":
            count_deletions -= 1
            count_additions -= 1

        else:
            c_section = 'unchanged_text'
            # if we came out of a change hunk section we can close this chunk
            # and append it to the chunks list
            if c_section != prev_section and prev_section != 'header':
                chunks.append(chunk)
                chunk = {
                    "added": [],
                    "deleted": [],
                }

        prev_section = c_section

    # flush the last change (if present)
    if len(chunk['added']) > 0 or len(chunk['deleted']) > 0:
        chunks.append(chunk)

    return chunks


def compute_diff_per_file(
        path_repo_folder: str,
        repos_subfolders: List[str]):
    """Compute diff metrics for each file in the repo-specific folders."""
    reports = []

    for repo_name in repos_subfolders:

        path_repo = os.path.join(path_repo_folder, repo_name)
        repo_bugs = os.listdir(path_repo)

        for bug_folder_name in repo_bugs:

            path_bug_folder = os.path.join(path_repo, bug_folder_name)

            folder_before = os.path.join(path_bug_folder, "before")
            folder_after = os.path.join(path_bug_folder, "after")

            # read metadata
            path_metadata = os.path.join(path_bug_folder, "metadata.json")
            with open(path_metadata, "r") as metadata_file:
                metadata = json.load(metadata_file)

            for name, content_before, content_after in iterate_over(
                    folder_master=folder_before,
                    folder_slave=folder_after):
                diffs = dl.unified_diff(
                    content_before.splitlines(False),
                    content_after.splitlines(False))
                text_diff = "\n".join(list(diffs))
                # remove the useless preface before the "@@" character
                text_diff = text_diff[text_diff.find("@@"):]
                # print(name)
                # print(text_diff)
                # print("-" * 80)
                # print("HUNKS:")
                # print("-" * 80)
                hunks = get_hunks(text_diff)
                # count the lines
                n_modified_lines = 0
                for h_i, hunk in enumerate(hunks):
                    # print(f"Hunk {h_i}")
                    # print(hunk)
                    i_modified_lines = max(
                        len(hunk["deleted"]),
                        len(hunk["added"])
                    )
                    n_modified_lines += i_modified_lines
                # if the file has any change, store it
                if len(hunks) > 0:
                    report = {
                        "n_lines": n_modified_lines,
                        "n_hunks": len(hunks),
                        "filename": name,
                        "n_files": 1,
                        **metadata
                    }
                    reports.append(report)
    df_reports = pd.DataFrame.from_records(reports)
    return df_reports


def compute_diff_per_bug(
        path_repo_folder: str,
        repos_subfolders: List[str]):
    """Compute diff metrics for each bug in the repo-specific folders."""
    df_reports = compute_diff_per_file(path_repo_folder, repos_subfolders)
    df_grouped = df_reports.groupby(
        by=["human_id", "id", "project_name", "commit_hash"]
        ).sum().reset_index()
    df_grouped["comprehensive_id"] = df_grouped.apply(
        lambda row: f'{row["human_id"]} ({row["id"]})',
        axis=1
    )
    return df_grouped

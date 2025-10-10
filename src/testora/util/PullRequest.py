import requests
from unidiff import PatchSet
import re

from collections.abc import Generator
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.GithubException import UnknownObjectException
from re import Pattern
from typing import List, Tuple

from testora.util.PythonCodeUtil import equal_modulo_docstrings, extract_target_function_by_range, get_name_of_defined_function
from testora import Config


class PullRequest:
    def __init__(self, github_pr, github_repo, cloned_repo_manager, pr_nb):
        self.github_pr = github_pr
        self.cloned_repo_manager = cloned_repo_manager
        self.number = github_pr.number
        self.title = github_pr.title
        self.post_commit = github_pr.merge_commit_sha
        self.parents = github_repo.get_commit(self.post_commit).parents
        self.pre_commit = self.parents[0].sha

        self.github_repo = github_repo
        self.pr_nb = pr_nb

        self._pr_url_to_patch()
        self._compute_non_test_modified_files()
        self._compute_modified_lines()

    

    def _pr_url_to_patch(self): 
        ''' 
        The target is to get the modified files from the patch.
        (all the touch files in a PR, **exclude** deleted and newly added files). 
        '''

        # # option 1
        # diff_url = self.github_pr.html_url + ".diff"
        # diff = urllib.request.urlopen(diff_url)
        # encoding = diff.headers.get_charsets()[0]
        # self.patch = PatchSet(diff, encoding=encoding)

        # # option 2
        # if the above code hits the request limit, use the following instead.
        diff_url = self.github_pr.url
        token = open(".github_token", "r").read().strip()
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"}

        response = requests.get(diff_url, headers=headers)
        response.raise_for_status()

        # # Load diff with unidiff PatchSet
        self.patch = PatchSet(response.text) 

    def _compute_non_test_modified_files(self):
        module_name = self.cloned_repo_manager.module_name

        # Python files only
        modified_python_files = [
            f for f in self.patch.modified_files if f.path.endswith(".py") or f.path.endswith(".pyx")]
        self.non_test_modified_python_files = [
            f.path for f in modified_python_files if "test" not in f.path and (f.path.startswith(module_name) or f.path.startswith(f"src/{module_name}"))]

        # Python and other PLs
        modified_code_files = [
            f for f in self.patch.modified_files if
            f.path.endswith(".py") or
            f.path.endswith(".pyx") or
            f.path.endswith(".c") or
            f.path.endswith(".cpp") or
            f.path.endswith(".h")
        ]
        self.non_test_modified_code_files = [
            f.path for f in modified_code_files if "test" not in f.path and (f.path.startswith(module_name) or f.path.startswith(f"src/{module_name}"))]

    def get_modified_files(self):
        if Config.code_change_pl == "python":
            return self.non_test_modified_python_files
        elif Config.code_change_pl == "all":
            return self.non_test_modified_code_files

    def has_non_comment_change(self):
        if Config.code_change_pl == "all":
            return len(self.non_test_modified_code_files) > 0

        pre_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.pre_commit)
        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        self.files_with_non_comment_changes = []
        for modified_file in self.non_test_modified_python_files:
            with open(f"{pre_commit_cloned_repo.repo.working_dir}/{modified_file.path}", "r") as f:
                old_file_content = f.read()
            with open(f"{post_commit_cloned_repo.repo.working_dir}/{modified_file.path}", "r") as f:
                new_file_content = f.read()
            if not equal_modulo_docstrings(old_file_content, new_file_content):
                self.files_with_non_comment_changes.append(modified_file.path)

        self.files_with_non_comment_changes = list(dict.fromkeys(
            self.files_with_non_comment_changes))  # turn into set while preserving order
        return len(self.files_with_non_comment_changes) > 0

    def _get_relevant_changed_files(self) -> list[str]:
        if Config.code_change_pl == "python":
            return self.files_with_non_comment_changes
        elif Config.code_change_pl == "all":
            return self.non_test_modified_code_files
        else:
            raise Exception(
                f"Unexpected configuration value: {Config.code_change_pl}")

    def get_filtered_diff(self):
        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        diff_parts = []
        for file_path in self._get_relevant_changed_files():
            raw_diff = post_commit_cloned_repo.repo.git.diff(
                self.pre_commit, self.post_commit, file_path)
            diff_parts.append(raw_diff)

        return "\n\n".join(diff_parts)

    def get_full_diff(self):
        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        return post_commit_cloned_repo.repo.git.diff(self.pre_commit, self.post_commit)

    def get_changed_function_names(self):
        result = []

        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        for modified_file in self.patch.modified_files:
            if modified_file.path in self._get_relevant_changed_files():
                with open(f"{post_commit_cloned_repo.repo.working_dir}/{modified_file.path}", "r") as f:
                    new_file_content = f.read()

                module_name = modified_file.path.replace(
                    "/", ".").replace(".pyx", "").replace(".py", "")

                for hunk in modified_file:
                    start_line = hunk.target_start
                    end_line = hunk.target_start + hunk.target_length
                    patch_range = (start_line, end_line)
                    fct_code = extract_target_function_by_range(
                        new_file_content, patch_range)
                    if fct_code is not None:
                        fct_name = get_name_of_defined_function(fct_code)
                        if fct_name:
                            result.append(f"{module_name}.{fct_name}")

        result = list(dict.fromkeys(result))
        return result

    def _compute_modified_lines(self):
        self.old_file_path_to_modified_lines = {}
        self.new_file_path_to_modified_lines = {}

        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)
        diff = post_commit_cloned_repo.repo.git.diff(
            self.pre_commit, self.post_commit)
        patch = PatchSet(diff)

        for patched_file in patch:
            self.old_file_path_to_modified_lines[patched_file.path] = set()
            self.new_file_path_to_modified_lines[patched_file.path] = set()
            for hunk in patched_file:
                for line in hunk:
                    if line.is_removed:
                        self.old_file_path_to_modified_lines[patched_file.path].add(
                            line.source_line_no)
                    elif line.is_added:
                        self.new_file_path_to_modified_lines[patched_file.path].add(
                            line.target_line_no)
    

    def _get_reference_patterns_for_issues_and_pulls(self) -> List[Pattern]:
        patterns: List[Pattern] = []
        patterns.append(re.compile('gh-[0-9]+'))
        patterns.append(re.compile('GH-[0-9]+'))
        patterns.append(re.compile('#[0-9]+'))
        patterns.append(re.compile('/pull/[0-9]+'))
        patterns.append(re.compile('/issues/[0-9]+'))
        return patterns
    
    
    def _get_reference_patterns_for_comments(self) -> List[Pattern]:
        patterns: List[Pattern] = []
        patterns.append(re.compile('[0-9]+#discussion_r[0-9]+'))
        patterns.append(re.compile('[0-9]+#issuecomment-[0-9]+'))
        return patterns


    def _get_reference_comment_strings(self) -> List[List[str]]:
        patterns: List[Pattern] = self._get_reference_patterns_for_comments()
        pattern_results: List[List[str]] = []
        for pattern in patterns:
            # Remove duplicates from the findall() result
            result = list(set(pattern.findall(self.github_pr.body)))
            pattern_results.append(result)
        return pattern_results
        


    def _get_reference_issue_and_pull_numbers(self) -> Generator[List[str], List[str], None]:
        patterns: List[Pattern] = self._get_reference_patterns_for_issues_and_pulls()
        for pattern in patterns:
            yield pattern.findall(self.github_pr.body)


    def get_reference_comments(self) -> List[str]:
        comments: List[str] = []        
        number: Pattern = re.compile('[0-9]+')
        pattern_results: List[List[str]] = self._get_reference_comment_strings()
        for pattern_result in pattern_results:
            for reference in pattern_result:
                tmp_numbers: List[str] = number.findall(reference)
                github_object_nb: int = int(tmp_numbers[0])
                comment_nb: int = int(tmp_numbers[1])
                try:
                    issue = self.github_repo.get_issue(github_object_nb)
                    comments.append(issue.get_comment(comment_nb).body)
                except UnknownObjectException:
                    try:
                        pull = self.github_repo.get_pull(github_object_nb)
                        comments.append(pull.get_comment(comment_nb).body)
                    except UnknownObjectException:
                        raise RuntimeWarning(f"Repository {str(self.github_repo.name)} has no issue or PR with the number {github_object_nb}\n")
                    
        return comments


    def get_reference_issues_and_pulls(self) -> Tuple[List[Issue], List[PullRequest]]:
        issues: List[Issue] = []
        pull_requests: List[PullRequest] = []
        object_numbers: List[int] = []
        number: Pattern = re.compile('[0-9]+')
        for pattern_result in self._get_reference_issue_and_pull_numbers():
            for reference in pattern_result:
                github_object_nb = int(number.findall(reference)[0])
                if github_object_nb not in object_numbers:
                    try:
                        issue = self.github_repo.get_issue(github_object_nb)
                        object_numbers.append(github_object_nb)
                        issues.append(issue)
                    except UnknownObjectException:
                        try:
                            pull = self.github_repo.get_pull(github_object_nb)
                            object_numbers.append(github_object_nb)
                            pull_requests.append(pull)
                        except UnknownObjectException:
                            raise RuntimeWarning(f"Repository {str(self.github_repo.name)} has no issue or PR with the number {github_object_nb}\n")

        return issues, pull_requests
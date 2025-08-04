from unidiff import PatchSet
import urllib.request

from typing import List, Dict
from testora.util.Logs import append_event, PullRequestReferencesEvent

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
        diff_url = self.github_pr.html_url + ".diff"
        diff = urllib.request.urlopen(diff_url)
        encoding = diff.headers.get_charsets()[0]
        self.patch = PatchSet(diff, encoding=encoding)

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
    

    def get_references(self) -> List:
        issues = []
        comments = []

        referenced_issues = self._scan_for_reference_issues(self.github_pr.body)
        referenced_comments = self._scan_for_comments()

        append_event(PullRequestReferencesEvent(pr_nb=self.pr_nb,
                                                message="References",
                                                related_issues_count=len(referenced_issues),
                                                related_issues=str(referenced_issues),
                                                related_comments_count=len(referenced_comments),
                                                related_comments=str(referenced_comments)))

        for issue_nb in referenced_issues:
            issues.append(self.github_repo.get_issue(issue_nb))

        for elem in referenced_comments:
            comment = {}
            if "issue" in elem:
                issue_nb = elem["issue"]
                issue = self.github_repo.get_issue(issue_nb)
                comment_nb = elem["comment_nb"]
                comment["issue"] = issue_nb
                comment["comment_nb"] = comment_nb
                comment["content"] = issue.get_comment(comment_nb)
            elif "pull" in elem:
                pull_nb = elem["pull"]
                pull = self.github_repo.get_pull(pull_nb)
                comment_nb = elem["comment_nb"]
                comment["pull"] = pull_nb
                comment["comment_nb"] = comment_nb
                comment["content"] = pull.get_comment(comment_nb)
            else:
                raise RuntimeError("Neither pull or issue is a valid key in the elem dict")          
            
            comments.append(comment)

        return issues, comments

    
    # Refrerenced issues normally start with a '#' or 'gh-'
    # Returns: [<issue_num1>, <issue_num2>, ...], where issue_num* are integer
    def _scan_for_reference_issues(self, pr_body: str) -> List:
        result = []
        numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        state = 0
        token  = ""
        for i in range(len(pr_body)):
            char = pr_body[i]
            match state:
                case 0:
                    match char:
                        case "g":
                            state = 1
                        case "#":
                            state = 4
                        case _:
                            state = 0
                case 1:
                    match char:
                        case "h":
                            state = 3
                        case _:
                            state = 0
                case 3: 
                    match char:
                        case "-":
                            state = 4
                        case _:
                            state = 0
                case 4:
                    if char in numbers:
                        token += char
                        state = 4
                    else:
                        state = 5
                case 5:
                    # TODO: Consider to remove the restiction of lenght
                    if len(token) >= 5:
                        tmp = int(token)
                        if tmp not in result:
                            result.append(tmp)
                        token = ""
                        match char:
                            case "g":
                                state = 1
                            case "#":
                                state = 4
                            case _:
                                state = 0
                    else:
                        token = ""
                        match char:
                            case "g":
                                state = 1
                            case "#":
                                state = 4
                            case _:
                                state = 0
                case _:
                    raise RuntimeError("Should never reach this")           
        return result


    # Returns: [{"issue": <issue_num>, "comment_nb": <num>}, {"issue": <issue_num>, "comment_nb": <num>}, ...]
    def _scan_for_comments(self) -> List:
        body = self.github_pr.body
        result = []

        issues_link = "https://github.com/scipy/scipy/issues/"
        pull_link = "https://github.com/scipy/scipy/pull/"
        
        l1 = len(issues_link)
        l2 = len(pull_link)

        while True:
            if issues_link in body:
                tmp = body[body.find(issues_link) + l1:]
                if "#issuecomment-" in tmp:
                    pref, suff = tmp.split("#issuecomment-", maxsplit=1)
                    issue_cmt = self._scan_for_comments(pref, suff, issue_comment=True)
                    if issue_cmt != -1 and issue_cmt not in result:
                        result.append(issue_cmt)
                pre_suf = body.split(issues_link, maxsplit=1)
                body = pre_suf[0] + pre_suf[1]

            elif pull_link in body:
                tmp = body[body.find(pull_link) + l2:]
                if "#discussion_r" in tmp:
                    pref, suff = tmp.split("#discussion_r", maxsplit=1)
                    pull_cmt = self._scan_for_comments(pref, suff, issue_comment=False)
                    if pull_cmt != -1 and pull_cmt not in result:
                        result.append(pull_cmt)
                pre_suf = body.split(pull_link, maxsplit=1)
                body = pre_suf[0] + pre_suf[1]
            else:
                break
            
        return result
    

    def _scan_for_comments(self, pref: str, suff: str, issue_comment=False) -> Dict:
        result = {}
        if issue_comment:
            result["issue"] = int(pref) 
        else:
            result["pull"] = int(pref)

        suffix = suff
        numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        comment_nb = ""
        state = 0
        for i in range(len(suffix)):
            char = suffix[i]
            match state:
                case 0:
                    if char in numbers:
                        comment_nb += char
                        state = 1
                    else:
                        # Link has no valid comment number
                        return -1
                case 1:
                    if char in numbers:
                        comment_nb += char
                        state = 1
                    else:
                        state = 2
                case 2:
                    if len(comment_nb) >= 9:
                        result["comment_nb"] = int(comment_nb)
                        comment_nb = ""
                        return result
                    else:
                        # Link has no valid comment number
                        return -1
                case _:
                    raise RuntimeError("Should never reach this")
        raise RuntimeError("Should never reach this")
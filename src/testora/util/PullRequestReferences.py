from typing import List, Dict
from testora.util.Logs import append_event, PullRequestReferencesEvent

class PullRequestReferences:
    def __init__(self, github_repo, github_pr, pr_nb):
        self.pr = github_pr
        self.repo = github_repo
        self.pr_nb = pr_nb
        pass

    def get_references(self) -> List:
        issues = []
        comments = []

        referenced_issues = self.get_issues()
        referenced_comments = self.scan_for_comments()

        append_event(PullRequestReferencesEvent(pr_nb=self.pr_nb,
                                                message="References",
                                                related_issues_count=len(referenced_issues),
                                                related_issues=str(referenced_issues),
                                                related_comments_count=len(referenced_comments),
                                                related_comments=str(referenced_comments)))

        for issue_nb in referenced_issues:
            issues.append(self.repo.get_issue(issue_nb))

        for elem in referenced_comments:
            comment = {}
            if "issue" in elem:
                issue_nb = elem["issue"]
                issue = self.repo.get_issue(issue_nb)
                comment_nb = elem["comment_nb"]
                comment["issue"] = issue_nb
                comment["comment_nb"] = comment_nb
                comment["content"] = issue.get_comment(comment_nb)
            elif "pull" in elem:
                pull_nb = elem["pull"]
                pull = self.repo.get_pull(pull_nb)
                comment_nb = elem["comment_nb"]
                comment["pull"] = pull_nb
                comment["comment_nb"] = comment_nb
                comment["content"] = pull.get_comment(comment_nb)
            else:
                raise RuntimeError("Neither pull or issue is a valid key in the elem dict")          
            
            comments.append(comment)

        return issues, comments


    def get_issues(self) -> List:
        body = self.pr.body
        issues_numbers = []
    
        # Search for a specific Reference issue section in the PR body.
        # If this section does not exist, just scan the complete PR body
        if "#### Reference issue" in body:
        
            a = body.find("#### Reference issue")
            b = len("#### Reference issue")
            issues_body = body[a+b:]
    
            if "####" in issues_body:
                c = issues_body.find("####")
                issues_body = issues_body[:c]
            
            issues_numbers = self.scan_for_reference_issues(issues_body)
    
        else:
            issues_numbers = self.scan_for_reference_issues(body)
    
        return issues_numbers

    
    # Refrerenced issues normally start with a '#' or 'gh-'
    # Returns: [<issue_num1>, <issue_num2>, ...], where issue_num* are integer
    def scan_for_reference_issues(self, issues_body: str) -> List:
        result = []
        numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        state = 0
        token  = ""
        for i in range(len(issues_body)):
            char = issues_body[i]
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
    def scan_for_comments(self) -> List:
        body = self.pr.body
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
                    if issue_cmt != -1:
                        result.append(issue_cmt)
                pre_suf = body.split(issues_link, maxsplit=1)
                body = pre_suf[0] + pre_suf[1]

            elif pull_link in body:
                tmp = body[body.find(pull_link) + l2:]
                if "#discussion_r" in tmp:
                    pref, suff = tmp.split("#discussion_r", maxsplit=1)
                    pull_cmt = self._scan_for_comments(pref, suff, issue_comment=False)
                    if pull_cmt != -1:
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
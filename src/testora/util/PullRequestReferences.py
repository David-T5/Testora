from typing import List, Dict


class PullRequestReferences:
    def __init__(self, github_repo, github_pr):
        self.pr = github_pr
        self.repo = github_repo
        pass

    def get_issues(self) -> List:
        body = self.pr.body
        issues = []
    
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
    
        for number in issues_numbers:
            issues.append(self.repo.get_issue(number))
    
        return issues

    
    # Refrerenced issues normally start with a '#' or 'gh-'
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
                    pref, suff = tmp.split("#issuecomment-")
                    issue_cmt = self._scan_for_comments(pref, suff, issue_comment=True)
                    if issue_cmt != -1:
                        result.append(issue_cmt)
                pre_suf = body.split(issues_link)
                body = pre_suf[0] + pre_suf[1]

            elif pull_link in body:
                tmp = body[body.find(pull_link) + l2:]
                if "#discussion_r" in tmp:
                    pref, suff = tmp.split("#discussion_r")
                    pull_cmt = self._scan_for_comments(pref, suff, issue_comment=False)
                    if pull_cmt != -1:
                        result.append(pull_cmt)
                pre_suf = body.split(pull_link)
                body = pre_suf[0] + pre_suf[1]
            else:
                break
            
        return result
    

    def _scan_for_comments(self, pref: str, suff: str, issue_comment=False) -> Dict:
        result = {}
        if issue_comment:
            result["issue"] = pref
        else:
            result["pull"] = pref
        
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
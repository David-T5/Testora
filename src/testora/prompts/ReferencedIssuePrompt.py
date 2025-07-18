from testora.util.Logs import CreateIssuePromptEvent, append_event

class ReferencedIssuePrompt:
    def __init__(self, issue, pr_nb):
        self.pr_nb = pr_nb
        self.issue = issue
        self.issue_body = issue.body
        self.issue_number = issue.number
        self.issue_title = issue.title
        self.use_json_output = False

    def create_prompt(self):
        template ="""

<ADDITIONAL_INFORMATION>

The issue with the title {issue_title} is related to the Pull Request from 
the fist message. Please consider the following information from this
issue for answering the questions from the first message:

{issue}

</ADDITIONAL_INFORMATION>
"""
        length_body = len(self.issue_body)

        length_template = len(template)

        body = self.issue_body

        title = self.issue_title

        append_event(CreateIssuePromptEvent(pr_nb=self.pr_nb,
                                       message="Referenced Issue Prompt",
                                       length=length_template + len(body) + len(title),
                                       issue_nb=self.issue_number))

        if length_body + length_template > 60000:
            body = self.issue_body[:60000 - length_template - 1]
        
        return template.format(issue_title=title, issue=body)

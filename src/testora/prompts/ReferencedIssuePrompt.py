from testora.util.Logs import CreatePromptEvent, append_event

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
Please consider the following additional information:

<ADDITIONAL_INFORMATION>

{issue}

</ADDITIONAL_INFORMATION>
"""
        append_event(CreatePromptEvent(pr_nb=self.pr_nb,
                                       message="Referenced Issue Prompt",
                                       length=len(template)))

        length_body = len(self.issue_body)

        length_template = len(template)

        body = self.issue_body

        if length_body + length_template > 60000:
            body = self.issue_body[:60000 - length_template - 1]
        
        return template.format(issue=body)

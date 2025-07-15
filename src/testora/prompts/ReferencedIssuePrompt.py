class ReferencedIssuePrompt:
    def __init__(self, issue):
        self.issue = issue
        self.issue_body = issue.body
        self.use_json_output = False

    def create_prompt(self):
        template ="""
Please consider the following additional information:

<ADDITIONAL_INFORMATION>

{issue}

</ADDITIONAL_INFORMATION>
"""
        length_body = len(self.issue_body)

        length_template = len(template)

        body = self.issue_body

        if length_body + length_template > 60000:
            body = self.issue_body[:60000 - length_template - 1]
        
        return template.format(issue=body)

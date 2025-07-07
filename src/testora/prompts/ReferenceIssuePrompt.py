class ReferenceIssuePrompt:
    def __init__(self, issue):
        self.issue = issue
        self.issue_body = issue.body
        self.use_json_output = False

    def create_prompt(self):
        template ="""
Are you sure about your answers from 
the previous message, given the information
from the system message?
Please consider the following additional information:

<ADDITIONAL_INFORMATION>

{issue_information}

</ADDITIONAL_INFORMATION>

With these additional information and the information from the system message,
reconsider your answers for the questions in the system message
again and explain your reasoning and then give your answers in the following format:

<THOUGHTS>
...
</THOUGHTS>
<ANSWER1>
...
</ANSWER1>
<ANSWER2>
...
</ANSWER2>
<ANSWER3>
...
</ANSWER3>
<ANSWER4>
...
</ANSWER4>
<ANSWER5>
...
</ANSWER5>

"""
        length_body = len(self.issue_body)

        length_template = len(template)

        body = self.issue_body

        if length_body + length_template > 30000:
            body = self.issue_body[:30000 - length_template - 1]
        
        return template.format(issue_information=body)

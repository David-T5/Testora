from testora.util.Logs import CreatePromptEvent, append_event

class ReferencedCommentsPrompt:
    def __init__(self, comment, pr_nb):
        self.pr_nb = pr_nb
        self.comment = comment
        self.comment_body = comment.body
        self.use_json_output = False

    def create_prompt(self):
        template ="""
Please consider the following additional information:

<ADDITIONAL_INFORMATION>

{comment}

</ADDITIONAL_INFORMATION>
"""

        append_event(CreatePromptEvent(pr_nb=self.pr_nb,
                                       message="Referenced Comment Prompt",
                                       length=len(template)))

        length_body = len(self.comment_body)

        length_template = len(template)

        body = self.comment_body

        if length_body + length_template > 30000:
            body = self.comment_body[:30000 - length_template - 1]
        
        return template.format(comment=body)

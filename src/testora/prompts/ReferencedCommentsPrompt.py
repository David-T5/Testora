from testora.util.Logs import CreateCommentPromptEvent, append_event
from typing import Optional

class ReferencedCommentsPrompt:
    def __init__(self, comment, pr_nb):
        self.pr_nb = pr_nb
        self.comment = comment
        self.comment_body = comment["content"].body
        self.issue_nb = None
        self.pull_nb = None
        self.comment_nb = comment["comment_nb"]
        self.use_json_output = False

        if "issue" in list(comment.keys()):
            self.issue_nb = comment["issue"]
        elif "pull" in list(comment.keys()):
            self.pull_nb = comment["pull"]
        else:
            raise RuntimeError("comment Dict datastructure has not the intended format!")
        

    def create_prompt(self):
        template ="""

<ADDITIONAL_INFORMATION>

The following comment containts information which
should also be considered answering the questions from the 
first message:

{comment}

</ADDITIONAL_INFORMATION>
"""

        length_body = len(self.comment_body)

        length_template = len(template)

        body = self.comment_body

        append_event(CreateCommentPromptEvent(pr_nb=self.pr_nb,
                                       message="Referenced Comment Prompt",
                                       length=length_template + len(body),
                                       issue_nb=self.issue_nb,
                                       pull_nb=self.pull_nb,
                                       comment_nb=self.comment_nb))

        if length_body + length_template > 30000:
            body = self.comment_body[:30000 - length_template - 1]
        
        return template.format(comment=body)

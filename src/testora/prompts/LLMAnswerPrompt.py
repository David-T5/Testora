class LLMAnswerPrompt:
    def __init__(self):
        self.use_json_output = False

    def create_prompt(self):
        template ="""

Are you sure about your answers with the given information
from the first user message?
Please consider the additional from the
user messages with the <ADDITIONAL_INFORMATION> section.

With these additional information and the information from the first message,
reconsider your answers for the questions in the first message
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
        
        return template

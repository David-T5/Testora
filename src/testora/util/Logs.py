import json
import os
import fnmatch
from datetime import datetime, timedelta
import atexit
from typing import List, Optional
from pydantic import BaseModel


class Event(BaseModel):
    timestamp: str = ""
    pr_nb: int
    message: str


class PREvent(Event):
    title: str
    url: str


class TestExecutionEvent(Event):
    code: str
    output: str


class ComparisonEvent(Event):
    test_code: str
    old_output: str
    new_output: str


class PreClassificationEvent(Event):
    test_code: str
    old_output: str
    new_output: str


class ClassificationEvent(Event):
    is_relevant_change: Optional[bool]
    is_deterministic: Optional[bool]
    is_public: Optional[bool]
    is_legal: Optional[bool]
    is_surprising: Optional[bool]
    is_sufficient: Optional[bool]
    correct_output: Optional[int]
    old_is_crash: bool
    new_is_crash: bool


class SelectBehaviorEvent(Event):
    expected_output: int


class LLMEvent(Event):
    content: str


class ErrorEvent(Event):
    details: str


class CoverageEvent(Event):
    details: str


class ClassifierEvalEvent(Event):
    label: str
    predictions: str

class PullRequestReferencesEvent(Event):
    related_issues_count: int
    related_issues: str
    related_comments_count: int
    related_comments: str

class CreatePromptEvent(Event):
    length: int 

class CreateIssuePromptEvent(Event):
    length: int
    issue_nb: int 

class CreateCommentPromptEvent(Event):
    length: int
    issue_nb: Optional[int] = None
    pull_nb: Optional[int] = None
    comment_nb: int

events: List = []
last_time_stored = datetime.now()
last_file_stored_to: Optional[str] = None


def append_event(evt):
    global last_time_stored

    evt.timestamp = datetime.now().isoformat()
    events.append(evt)
    print(json.dumps(evt.dict(), indent=2))

    if datetime.now() - last_time_stored > timedelta(minutes=5):
        store_logs()
        last_time_stored = datetime.now()


def get_logs_as_json():
    return json.dumps([evt.dict() for evt in events], indent=2)


def store_logs():
    global last_file_stored_to
    timestamp = datetime.now().isoformat()
    event_dicts = [evt.dict() for evt in events]
    out_file = f"logs_{timestamp}.json"
    json.dump(event_dicts, open(out_file, "w"), indent=2)

    # remove previous log from this run
    if last_file_stored_to is not None:
        os.remove(last_file_stored_to)
    last_file_stored_to = out_file


def reset_logs():
    global events
    events = []
    last_file_stored_to = None


def start_logging():
    atexit.register(store_logs)

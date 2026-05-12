from draftlens_api.engine.cycle_ledger_compare import count_new_material_issues, detect_text_thrash
from draftlens_api.domain.enums import IssueCategory, IssueSeverity
from draftlens_api.domain.models import Issue


def _issue(**kwargs):
    base = dict(
        block_id="b1",
        span_text="hello world",
        char_start=0,
        char_end=5,
        category=IssueCategory.clarity,
        severity=IssueSeverity.minor,
        title="t",
        explanation="e",
    )
    base.update(kwargs)
    return Issue(**base)


def test_count_new_material_detects_new_span():
    prior = [_issue(severity=IssueSeverity.minor, span_text="old")]
    cur = prior + [_issue(severity=IssueSeverity.major, span_text="brand new phrase", issue_id="x2")]
    n = count_new_material_issues(prior, cur, material_severities={"critical", "major", "minor"})
    assert n >= 1


def test_thrash_detection():
    assert detect_text_thrash(["a", "b", "a"]) is True
    assert detect_text_thrash(["a", "b", "c"]) is False

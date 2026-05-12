from draftlens_api.providers.structured_output import extract_first_json_value, parse_as_object, strip_code_fences


def test_strip_fence():
    s = "```json\n{\"a\": 1}\n```"
    assert strip_code_fences(s).startswith("{")


def test_extract_with_trailing_prose():
    raw = 'Here you go:\n{"summary": "x", "risks": [], "questions_for_peers": [], "issues": []}\nThanks.'
    v = extract_first_json_value(raw)
    assert isinstance(v, dict)
    assert v.get("summary") == "x"


def test_parse_as_object_rejects_array():
    pr = parse_as_object("[1,2]")
    assert pr.payload is None

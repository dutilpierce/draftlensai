from draftlens_api.policies.artifact_visibility import artifact_tier, annotate_rows


def test_tier_review():
    assert artifact_tier("issues.json", output_mode="review") == "advanced"
    assert artifact_tier("reviewed.docx", output_mode="review") == "primary"
    assert artifact_tier("redline.pdf", output_mode="review") == "primary"


def test_annotate_rows():
    rows = [{"name": "issues.json", "path": "/x", "media_type": "application/json"}]
    out = annotate_rows(rows, output_mode="review")
    assert out[0]["tier"] == "advanced"

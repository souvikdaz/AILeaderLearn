import pytest
from core.content_validator import validate_all_content

def test_validate_all_content():
    result = validate_all_content()
    # Phase 1, Phase 3 Generative AI modules, and outlines must all pass
    assert result["passed"] is True
    assert result["error_count"] == 0
    assert result["modules_validated"] >= 6

import pytest
from core.content_validator import validate_all_content

def test_validate_all_content():
    result = validate_all_content()
    # Entire Phase 1 curriculum and Phase 2-4 outlines must pass
    assert result["passed"] is True
    assert result["error_count"] == 0
    assert result["modules_validated"] == 4

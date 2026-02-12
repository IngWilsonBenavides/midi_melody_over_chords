from dictados.config import DictationSpec
from dictados.validation.spec_validator import validate_spec


def test_spec_validator_errors():
    spec = DictationSpec.model_validate(
        {
            "key": "C",
            "progression": [],
            "groups": 1,
            "subdivision": "quarter",
            "sequence": "1234",
            "range": [41, 81],
        }
    )
    errors = validate_spec(spec)
    assert "progression must not be empty" in errors

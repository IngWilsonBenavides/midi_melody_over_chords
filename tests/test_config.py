import pytest

from dictados.config import DictationSpec


def test_config_valid():
    spec = DictationSpec.model_validate(
        {
            "key": "C",
            "progression": ["I", "iv"],
            "groups": 2,
            "subdivision": "quarter",
            "sequence": "1234",
            "range": [41, 81],
            "tempo": 100,
            "ppqn": 480,
        }
    )
    assert spec.key == "C"


def test_config_invalid_sequence():
    with pytest.raises(ValueError):
        DictationSpec.model_validate(
            {
                "key": "C",
                "progression": ["I"],
                "groups": 1,
                "subdivision": "quarter",
                "sequence": "1123",
                "range": [41, 81],
            }
        )

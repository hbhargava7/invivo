import pandas as pd
import pytest

from invivo.io import extract_group_id, normalize_animal_ids


def test_normalize_animal_ids_accepts_canonical_format():
    animal_ids = pd.Series(['1-2', '10-42'])

    normalized = normalize_animal_ids(animal_ids)

    assert normalized.tolist() == ['1-2', '10-42']


def test_normalize_animal_ids_converts_group_prefixed_format():
    animal_ids = pd.Series(['Group 01-002', 'Group 12-034'])

    normalized = normalize_animal_ids(animal_ids)

    assert normalized.tolist() == ['1-2', '12-34']


def test_normalize_animal_ids_accepts_mixed_supported_formats():
    animal_ids = pd.Series(['1-2', 'Group 03-004'])

    normalized = normalize_animal_ids(animal_ids)

    assert normalized.tolist() == ['1-2', '3-4']


def test_normalize_animal_ids_reports_incompatible_values_without_dropping():
    animal_ids = pd.Series(['1-2', 'Mouse 3', None, 'Group 04-005'])

    with pytest.raises(ValueError) as error:
        normalize_animal_ids(animal_ids)

    message = str(error.value)
    assert '2 record(s)' in message
    assert "'Mouse 3'" in message
    assert '<missing>' in message
    assert '"1-2"' in message
    assert '"Group 01-002"' in message
    assert 'No records were dropped.' in message


def test_extract_group_id_supports_group_prefixed_format():
    data = pd.DataFrame({'Animal ID': ['Group 01-002', '3-4']})

    result = extract_group_id(data)

    assert result['Animal ID'].tolist() == ['1-2', '3-4']
    assert result['Group ID'].tolist() == [1, 3]

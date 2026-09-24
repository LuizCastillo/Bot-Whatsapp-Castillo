from app.utils.phone import normalize_br_phone


def test_adds_ninth_digit():
    assert normalize_br_phone("551199999999") == "5511999999999"


def test_keeps_canonical():
    assert normalize_br_phone("+55 (11) 99999-9999") == "5511999999999"


def test_landline_untouched():
    assert normalize_br_phone("551132223333") == "551132223333"

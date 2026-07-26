from parser import parse_form
import json


def test_income_aliases():
    s = "Name: John Doe\nSalary: 50000\n"
    lines = s.splitlines(True)
    parsed, seen_keys = parse_form(lines)

    assert parsed["Monthly Income"] == "50000"
    assert "Monthly Income" in seen_keys


def test_separator_line_terminates_last_field():
    s = "Name: John Doe\nSalary: 50000\n*****************\n"
    lines = s.splitlines(True)
    parsed, seen_keys = parse_form(lines)

    assert parsed["Monthly Income"] == "50000"
    assert "Monthly Income" in seen_keys
    assert parsed["Monthly Income"] != "*****************"


def test_summary_after_separator_until_rishta_given():
    s = (
        "Name: John Doe\n"
        "Salary: 50000\n"
        "*****************\n"
        "This is the summary text.\n"
        "It continues on a new line.\n"
        "Rishta Given: 1. Item one\n"
        "2. Item two\n"
    )
    lines = s.splitlines(True)
    parsed, seen_keys = parse_form(lines)

    assert parsed["Summary"] == "This is the summary text. It continues on a new line."
    assert parsed["Rishta Given"] == ["Item one", "Item two"]
    assert "Summary" in seen_keys
    assert "Rishta Given" in seen_keys


def test_phone_number_aliases():
    variants = [
        "Number: 12345",
        "Phone No: 12345",
        "Phone No.: 12345",
        "WN Number: 12345",
        "WN: 12345",
        "Whatsapp Number: 12345",
        "WhatApp No: 12345",
        "WhatApp No.: 12345",
        "WhatsApp No: 12345",
        "WhatsApp No.: 12345",
    ]
    for variant in variants:
        lines = f"Name: John Doe\n{variant}\n".splitlines(True)
        parsed, seen_keys = parse_form(lines)
        assert parsed["WhatsApp No"] == "12345"
        assert "WhatsApp No" in seen_keys


def test_whatsapp_no_strips_registration_form():
    s = "Name: John Doe\nWN: 12345 Registration Form\n"
    lines = s.splitlines(True)
    parsed, seen_keys = parse_form(lines)

    assert parsed["WhatsApp No"] == "12345"
    assert "WhatsApp No" in seen_keys


def test_rishta_given_ordered_list_parsing():
    s = (
        "Name: John Doe\n"
        "Rishta Given: 1. Item one\n"
        "2. Item two\n"
        "3. Item three\n"
    )
    lines = s.splitlines(True)
    parsed, seen_keys = parse_form(lines)

    assert parsed["Rishta Given"] == ["Item one", "Item two", "Item three"]
    assert "Rishta Given" in seen_keys


if __name__ == "__main__":
    test_income_aliases()
    test_separator_line_terminates_last_field()
    test_summary_after_separator_until_rishta_given()
    test_phone_number_aliases()
    test_rishta_given_ordered_list_parsing()
    print("test passed")

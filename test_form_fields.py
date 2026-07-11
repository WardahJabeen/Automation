from parser import parse_form


def test_special_urdu_fields_map_to_short_storage_keys():
    lines = [
        "Kya aap ke paas Divorce/Khula certificate hai?: yes\n",
        "Female: Kya aap First wife ki mojoodgi mei 2nd wife banney ko tayyar hain?: yes\n",
        "Sawal. Aap First wife ki mojoodgi mei 2nd marriage kiyun kerna chahtay hain?: reason\n",
        "Sawal: Ky aap ke paas 2nd marriage ke liye Govt Permission hai? : granted\n",
    ]

    form_data, _ = parse_form(lines)

    assert form_data["divorce_certificate"] == "yes"
    assert form_data["second_wife_ok"] == "yes"
    assert form_data["second_marriage_reason"] == "reason"
    assert form_data["govt_permission"] == "granted"

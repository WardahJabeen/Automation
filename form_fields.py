import difflib
import re

FORM_FIELDS = [
    "Registration No",
    "Date",
    "Name",
    "Guardian Name",
    "Relationship with Guardian",

    "Age",
    "Gender",
    "Marital Status",
    "No of Children",

    "Religion",
    "Maslak",
    "Kya aap Milaad/Nazr Niyaz/Fateha maantay hain?",
    "Caste",
    "Mother Tongue",

    "Height",
    "Complexion",
    "Any Physical Illness",
    "Any Physical Disability",

    "Qualification",
    "Job & Profession",
    "Monthly Income",
    "Girl/Woman: Ghar ka kya kya kaam aata hai?",

    "Your Current City",
    "State/Province",
    "Country",
    "Nationality/Visa Status",
    "In Pakistan from which city you belongs to",

    "About Father",
    "About Mother",
    "About Sisters",
    "About Brothers",

    "About Your Personality",
    "About Your Hobby",
    "Any other detail",

    "About your Home: Size? Own/Rent?",
    "Your Living Standard",
    "Your Social Class",

    "Your Requirements in Detail",
    "Profile Posted By",
    "City & Country",
    "Other details",

    "Kya aap ke paas Divorce/Khula certificate hai?:",
    "Female: Kya aap First wife ki mojoodgi mei 2nd wife banney ko tayyar hain?:",
    "Sawal. Aap First wife ki mojoodgi mei 2nd marriage kiyun kerna chahtay hain?",
    "Sawal: Ky aap ke paas 2nd marriage ke liye Govt Permission hai? ",
]

REQUIREMENT_DUPLICATE_FIELDS = {
    "Marital Status": "Requirements Marital Status",
    "Age": "Requirements Age",
    "Qualification": "Requirements Qualification",
    "Caste": "Requirements Caste",
    "Height": "Requirements Height",
    # "City & Country": "Requirements City & Country",
    # "Other details": "Requirements Other details",
}

FIELD_STORAGE_KEYS = {
    "Kya aap ke paas Divorce/Khula certificate hai?:": "divorce_certificate",
    "Female: Kya aap First wife ki mojoodgi mei 2nd wife banney ko tayyar hain?:": "second_wife_ok",
    "Sawal. Aap First wife ki mojoodgi mei 2nd marriage kiyun kerna chahtay hain?": "second_marriage_reason",
    "Sawal: Ky aap ke paas 2nd marriage ke liye Govt Permission hai? ": "govt_permission",
}


ALL_FIELDS = [FIELD_STORAGE_KEYS.get(field, field) for field in FORM_FIELDS] + list(REQUIREMENT_DUPLICATE_FIELDS.values())
SECTION_HEADER = "Your Requirements in Detail"


def normalize_key(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(text):
    text = text.strip()
    text = re.sub(r"[^a-zA-Z0-9: /?&\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_storage_key(field):
    return FIELD_STORAGE_KEYS.get(field, field)


def build_key_map():
    return {normalize_key(field): get_storage_key(field) for field in FORM_FIELDS}


def get_default_form_data():
    return {field: "" for field in ALL_FIELDS}


def resolve_key(raw_key, key_map, threshold=0.75):
    cleaned = normalize_key(raw_key)
    exact = key_map.get(cleaned)
    if exact:
        return exact

    best_matches = difflib.get_close_matches(cleaned, key_map.keys(), n=1, cutoff=threshold)
    if best_matches:
        return key_map[best_matches[0]]

    return None


import json
import re
from db import Database
from parser import parse_form


def prompt_menu(prompt, options):
    print(prompt)
    for num, text in options.items():
        print(f"{num}. {text}")
    return input().strip()


def read_multiline_form():
    print("Paste the whole form text. Enter a single '.' on its own line to finish.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        lines.append(line + "\n")
    return lines


def request_existing_phone(db):
    while True:
        phone_number = input("Phone number: ").strip()
        if not phone_number:
            print("Phone number cannot be empty.")
            continue
        if not db.whatsapp_no_exists(phone_number):
            print("Phone number not found in table. Please enter an existing WhatsApp No.")
            continue
        return phone_number


def request_phone_or_cancel(db, prompt_text="Phone number of candidate (or blank to cancel): "):
    while True:
        phone_number = input(prompt_text).strip()
        if not phone_number:
            return None
        if not db.whatsapp_no_exists(phone_number):
            print("Phone number not found in table. Please enter an existing WhatsApp No.")
            continue
        return phone_number


def prompt_summary_save_mode():
    while True:
        answer = prompt_menu(
            "Save summary mode:",
            {"1": "append", "2": "overwrite"},
        )
        if answer == "1" or answer.lower() == "append":
            return True
        if answer == "2" or answer.lower() == "overwrite":
            return False
        print("Unknown choice. Please choose 1 or 2.")


def parse_height(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None

    # normalize common height notation
    text = text.replace('”', '"').replace('“', '"').replace('’', "'").replace('‘', "'")

    cm_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*cm\b', text)
    if cm_match:
        return float(cm_match.group(1))

    m_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*m\b', text)
    if m_match and 'cm' not in text:
        meters = float(m_match.group(1))
        return meters * 100

    feet_inches = re.search(r'([0-9]+)\s*(?:ft|feet|foot)\s*(?:([0-9]+)\s*(?:in|inch|inches)?)?', text)
    if feet_inches:
        feet = float(feet_inches.group(1))
        inches = float(feet_inches.group(2) or 0)
        return feet * 30.48 + inches * 2.54

    feet_inch = re.search(r"([0-9]+)\s*'\s*([0-9]+)\s*(?:\"|in|inch|inches)?", text)
    if feet_inch:
        feet = float(feet_inch.group(1))
        inches = float(feet_inch.group(2))
        return feet * 30.48 + inches * 2.54

    decimal_feet = re.search(r'\b([4-7](?:\.[0-9]+)?)\b', text)
    if decimal_feet and ('ft' in text or 'feet' in text or 'foot' in text or '.' in decimal_feet.group(1)):
        feet = float(decimal_feet.group(1))
        return feet * 30.48

    number = re.search(r'\b([0-9]+(?:\.[0-9]+)?)\b', text)
    if number:
        value_num = float(number.group(1))
        if 100 <= value_num <= 250:
            return value_num
        if 4 <= value_num <= 8:
            return value_num * 30.48
        if 50 <= value_num <= 90:
            return value_num * 2.54

    return None


def normalize_country(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if 'pakistan' in text:
        return 'pakistan'
    return text


def parse_age(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None

    age_match = re.search(r'(\d{1,3})', text)
    if not age_match:
        return None

    age = int(age_match.group(1))
    if 10 <= age <= 120:
        return age
    return None


def get_age_range_index(age):
    if age is None:
        return None
    if 18 <= age <= 24:
        return 0
    if 25 <= age <= 28:
        return 1
    if 29 <= age <= 32:
        return 2
    if 33 <= age <= 36:
        return 3
    if 37 <= age <= 40:
        return 4
    if 41 <= age <= 75:
        return 5
    return None


def get_age_match_category(candidate_gender, candidate_age_range, match_gender, match_age_range):
    if candidate_age_range is None or match_age_range is None:
        return 3
    if candidate_gender not in {"male", "female"} or match_gender not in {"male", "female"}:
        return 3

    if candidate_gender == "male":
        male_age_range = candidate_age_range
        female_age_range = match_age_range
    else:
        male_age_range = match_age_range
        female_age_range = candidate_age_range

    if male_age_range == female_age_range + 1:
        return 0
    if female_age_range == male_age_range + 1:
        return 1
    if male_age_range == female_age_range:
        return 2
    return 3


def country_priority(country, candidate_country):
    normalized = normalize_country(country)
    if candidate_country == "pakistan":
        return 0 if normalized == "pakistan" else 1
    return 0 if normalized != "pakistan" else 1


def run_get_matching_flow(db):
    # Prompt user for a phone number to look up and show opposite-gender matches.
    while True:
        phone_number = input("Phone number of candidate (or blank to cancel): ").strip()
        if not phone_number:
            return

        profile = db.get_profile(phone_number)
        if not profile:
            print("No profile found for that WhatsApp No.")
            return

        gender_value = profile.get("Gender") or profile.get("gender") or ""
        opposite_gender_synonyms = get_opposite_gender_synonyms(gender_value)
        if not opposite_gender_synonyms:
            print(f"Could not determine opposite gender for '{gender_value}'.")
            return

        marital_value = profile.get("Marital Status") or profile.get("marital status") or ""
        marital_status_synonyms = get_matching_marital_status_synonyms(marital_value)
        if not marital_status_synonyms:
            print(f"Could not determine marital status for '{marital_value}'.")
            return

        candidate_height = parse_height(profile.get("Height") or profile.get("height") or "")
        if candidate_height is None:
            print("Could not determine height for the selected profile.")
            return

        candidate_age = parse_age(profile.get("Age") or profile.get("age") or "")
        candidate_age_range = get_age_range_index(candidate_age)

        matches = db.get_profiles_by_gender_and_marital_status(
            opposite_gender_synonyms,
            marital_status_synonyms,
            exclude_phone=phone_number,
        )
        if not matches:
            print("No opposite-gender matches found.")
            return

        filtered_matches = []
        candidate_gender = normalize_gender(gender_value)
        for match_profile in matches:
            match_gender = normalize_gender(match_profile.get("Gender") or match_profile.get("gender") or "")
            match_height = parse_height(match_profile.get("Height") or match_profile.get("height") or "")
            if match_height is None:
                continue

            if candidate_gender == "male" and match_gender == "female":
                if candidate_height >= match_height:
                    filtered_matches.append(match_profile)
            elif candidate_gender == "female" and match_gender == "male":
                if match_height >= candidate_height:
                    filtered_matches.append(match_profile)
            else:
                filtered_matches.append(match_profile)

        if not filtered_matches:
            print("No height-compatible opposite-gender matches found.")
            return

        candidate_country = normalize_country(profile.get("Country") or profile.get("country") or "")

        match_items = []
        for match_profile in filtered_matches:
            match_gender = normalize_gender(match_profile.get("Gender") or match_profile.get("gender") or "")
            match_age = parse_age(match_profile.get("Age") or match_profile.get("age") or "")
            match_age_range = get_age_range_index(match_age)
            category = get_age_match_category(
                candidate_gender,
                candidate_age_range,
                match_gender,
                match_age_range,
            )
            priority = country_priority(match_profile.get("Country") or match_profile.get("country") or "", candidate_country)
            match_items.append((category, priority, match_profile))

        match_items.sort(key=lambda item: (item[0], item[1]))
        ordered_matches = [item[2] for item in match_items]

        print(f"Found {len(ordered_matches)} opposite-gender match(es) after height filtering:")
        show_matches_paginated(ordered_matches)
        return


def show_matches_paginated(matches, page_size=10):
    total = len(matches)
    page_start = 0
    while page_start < total:
        page_end = min(page_start + page_size, total)
        for idx in range(page_start, page_end):
            print(f"--- Match {idx + 1} ---")
            print(format_db_value(matches[idx].get("Summary")))

        if page_end >= total:
            return

        while True:
            answer = input("Show next 10 matches or done? (next/done): ").strip().lower()
            if answer in {"next", "n"}:
                break
            if answer in {"done", "d"}:
                return
            print("Unknown choice. Please type 'next' or 'done'.")
        page_start = page_end


def format_db_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return ", ".join(str(item) for item in parsed)
            except Exception:
                pass
    return str(value)


def normalize_gender(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    female_terms = {
        "female", "woman", "women", "girl", "girls", "daughter", "mother", "sister", "wife", "mrs", "miss", "ms", "f",
    }
    male_terms = {
        "male", "man", "men", "boy", "boys", "son", "father", "brother", "husband", "mr", "m",
    }

    parts = text.split()
    for part in parts:
        if part in female_terms:
            return "female"
        if part in male_terms:
            return "male"

    # fallback exact tokens
    if text in female_terms:
        return "female"
    if text in male_terms:
        return "male"
    if "female" in text or "woman" in text or "girl" in text or "daughter" in text or "mother" in text or "sister" in text:
        return "female"
    if "male" in text or "man" in text or "boy" in text or "son" in text or "father" in text or "brother" in text:
        return "male"

    return ""


def get_opposite_gender_synonyms(gender_value):
    gender = normalize_gender(gender_value)
    if gender == "female":
        return ["male", "man", "men", "boy", "boys", "son", "father", "brother", "husband", "mr", "m"]
    if gender == "male":
        return ["female", "woman", "women", "girl", "girls", "daughter", "mother", "sister", "wife", "mrs", "miss", "ms", "f"]
    return []


def normalize_marital_status(text):
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    single_terms = {
        "single", "unmarried", "un-married", "never married", "nevermarried", "not married", "notmarried",
    }
    married_terms = {
        "married", "taken", "divorced", "widowed", "divorce", "widow", "kids", "children", "separated",
    }

    parts = text.split()

    print("text in normalized status" + text)
    if text in single_terms:
        return "single"
    if text in married_terms:
        return "married"
    if re.search(r"\b(?:single|unmarried|un married|never married|nevermarried|not married|notmarried)\b", text):
        return "single"
    if re.search(r"\b(?:married|taken|divorced|widowed|divorce|widow|kids|children|separated)\b", text):
        return "married"
    return ""


def get_matching_marital_status_synonyms(status_value):
    status = normalize_marital_status(status_value)
    if status == "single":
        return ["single", "un-married", "unmarried", "never married", "nevermarried"]
    if status == "married":
        return ["married", "taken", "divorced", "widowed", "divorce", "widow", "kids", "children", "separated"]
    return []


def run_get_profile_flow(db):
    phone_number = request_existing_phone(db)
    active_view = None

    while True:
        answer = prompt_menu(
            "Select an action:",
            {"1": "get full profile", "2": "get summary", "3": "cancel"},
        )
        if answer == "3" or answer.lower() == "cancel":
            return
        if answer == "1" or answer.lower() == "get full profile":
            profile = db.get_profile(phone_number)
            if not profile:
                print("No profile found for that WhatsApp No.")
                return
            print("Full profile:")
            for key, value in profile.items():
                print(f"{key}: {format_db_value(value)}")
            active_view = "full"
            break
        if answer == "2" or answer.lower() == "get summary":
            summary = db.get_summary(phone_number)
            if summary is None or summary == "":
                print("No summary found for that WhatsApp No.")
            else:
                print("Summary:")
                print(summary)
            active_view = "summary"
            break
        print("Unknown choice. Please choose 1, 2, or 3.")

    while True:
        other_action = "get summary" if active_view == "full" else "get full profile"
        shown_message = "Full profile has been shown above." if active_view == "full" else "Summary has been shown above."
        answer = prompt_menu(
            f"{shown_message}\nSelect an action:",
            {"1": "done", "2": other_action},
        )
        if answer == "1" or answer.lower() == "done":
            return
        if answer == "2" or answer.lower() == other_action:
            if active_view == "full":
                summary = db.get_summary(phone_number)
                if summary is None or summary == "":
                    print("No summary found for that WhatsApp No.")
                else:
                    print("Summary:")
                    print(summary)
                active_view = "summary"
            else:
                profile = db.get_profile(phone_number)
                if not profile:
                    print("No profile found for that WhatsApp No.")
                    return
                print("Full profile:")
                for key, value in profile.items():
                    print(f"{key}: {format_db_value(value)}")
                active_view = "full"
            continue
        print("Unknown choice. Please choose 1 or 2.")


def run_summary_flow(db):
    while True:
        phone_number = request_phone_or_cancel(db)
        if not phone_number:
            return

        while True:
            summary_text = input("Summar2 detail (or blank to cancel): ").strip()
            if not summary_text:
                return
            append = prompt_summary_save_mode()
            db.save_summary(phone_number, summary_text, append=append)
            print(f"Summary {'appended' if append else 'overwritten'} for {phone_number}.")
            return


def run_new_form_flow(db):
    print("Enter the new form details.")
    lines = read_multiline_form()
    if not lines:
        print("No form text entered.")
        return

    parsed, _ = parse_form(lines)
    whatsapp_no = parsed.get("WhatsApp No")
    if whatsapp_no and db.whatsapp_no_exists(whatsapp_no):
        print(f"A form with {whatsapp_no} number already exists in the table.")
        return
    try:
        db.insert_form(parsed)
        print("Form inserted successfully.")
    except Exception as exc:
        print(f"Failed to insert form: {exc}")
        return

    while True:
        answer = prompt_menu(
            "Select an action:",
            {"1": "enter summary", "2": "done"},
        )
        if answer == "2" or answer.lower() == "done":
            break
        if answer == "1" or answer.lower() == "enter summary":
            summary_text = input("Summary: ").strip()
            if summary_text:
                phone_number = parsed.get("WhatsApp No")
                if not phone_number:
                    print("WhatsApp No could not be parsed from the form. Please enter an existing phone number.")
                    phone_number = request_existing_phone(db)
                append = prompt_summary_save_mode()
                db.save_summary(phone_number, summary_text, append=append)
                print(f"Summary {'appended' if append else 'overwritten'} for {phone_number}.")
            else:
                print("Summary cannot be empty.")
            break
        print("Unknown choice. Please choose 1 or 2.")


def run_rishta_given_flow(db):
    phone_number = request_phone_or_cancel(db)
    if not phone_number:
        return

    entered_any = False
    while True:
        detail = input("Rishta detail (or blank to cancel): ").strip()
        if not detail:
            break
        db.append_rishta_given(phone_number, [detail])
        print(f"Added Rishta Given item for {phone_number}.")
        entered_any = True

    if not entered_any:
        print("No Rishta Given items were entered.")


def run_main_loop():
    db = Database()
    try:
        while True:
            answer = prompt_menu(
                "Select an action:",
                {"1": "enter new form", "2": "enter Rishta given", "3": "enter summary", "4": "get profile", "5": "get matching", "6": "done"},
            )
            if answer == "6" or answer.lower() == "done":
                break
            if answer == "2" or answer.lower() == "enter rishta given":
                run_rishta_given_flow(db)
                continue
            if answer == "3" or answer.lower() == "enter summary":
                run_summary_flow(db)
                continue
            if answer == "4" or answer.lower() == "get profile":
                run_get_profile_flow(db)
                continue
            if answer == "5" or answer.lower() == "get matching":
                run_get_matching_flow(db)
                continue
            if answer == "1" or answer.lower() == "enter new form":
                run_new_form_flow(db)
                continue
            print("Unknown choice. Please choose 1, 2, 3, 4, 5, or 6.")
    finally:
        db.close()


if __name__ == "__main__":
    run_main_loop()

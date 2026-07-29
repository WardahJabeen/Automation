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
    print("Paste the whole form text. Enter an empty line twice or a single '.' on its own line to finish.")
    lines = []
    blank_line_seen = False
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        if line == "":
            if blank_line_seen:
                break
            blank_line_seen = True
            continue
        blank_line_seen = False
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


def run_get_matching_flow(db):
    # Prompt user for a phone number to look up and show opposite-gender matches.
    while True:
        phone_number = input("Phone number to match (or blank to cancel): ").strip()
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

        matches = db.get_profiles_by_gender_synonyms(opposite_gender_synonyms, exclude_phone=phone_number)
        if not matches:
            print("No opposite-gender matches found.")
            return

        print(f"Found {len(matches)} opposite-gender match(es):")
        for idx, match_profile in enumerate(matches, start=1):
            print(f"--- Match {idx} ---")
            print(format_db_value(match_profile.get("Summary")))
        return


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
        answer = prompt_menu(
            "Select an action:",
            {"1": "enter the phone number", "2": "done"},
        )
        if answer == "2" or answer.lower() == "done":
            return
        if answer == "1" or answer.lower() == "enter the phone number":
            phone_number = request_existing_phone(db)
            while True:
                answer = prompt_menu(
                    "Select an action:",
                    {"1": "enter summary details", "2": "done"},
                )
                if answer == "2" or answer.lower() == "done":
                    return
                if answer == "1" or answer.lower() == "enter summary details":
                    summary_text = input("Summary: ").strip()
                    if summary_text:
                        append = prompt_summary_save_mode()
                        db.save_summary(phone_number, summary_text, append=append)
                        print(f"Summary {'appended' if append else 'overwritten'} for {phone_number}.")
                    else:
                        print("Summary cannot be empty.")
                    return
                print("Unknown choice. Please choose 1 or 2.")
        else:
            print("Unknown choice. Please choose 1 or 2.")


def run_new_form_flow(db):
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
    while True:
        answer = prompt_menu(
            "Select an action:",
            {"1": "enter the phone number", "2": "cancel"},
        )
        if answer == "2" or answer.lower() == "cancel":
            return
        if answer == "1" or answer.lower() == "enter the phone number":
            phone_number = request_existing_phone(db)

            entered_any = False
            while True:
                answer = prompt_menu(
                    "Select an action:",
                    {"1": "enter the rishta detail", "2": "done"},
                )
                if answer == "2" or answer.lower() == "done":
                    break
                if answer == "1" or answer.lower() == "enter the rishta detail":
                    detail = input("Rishta detail: ").strip()
                    if detail:
                        db.append_rishta_given(phone_number, [detail])
                        print(f"Added Rishta Given item for {phone_number}.")
                        entered_any = True
                    else:
                        print("Detail cannot be empty.")
                    continue
                print("Unknown choice. Please choose 1 or 2.")

            if not entered_any:
                print("No Rishta Given items were entered.")
            return

        print("Unknown choice. Please choose 1 or 2.")


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

import sys
import re

import re

def normalize_key(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", "", text)  # remove punctuation
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize(text):
    # Remove special characters (keep letters, numbers, spaces, colon)
    text = re.sub(r"[^a-zA-Z0-9: ]+", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text

def resolve_key(raw_key, key_map):
    cleaned = normalize_key(raw_key)
    return key_map.get(cleaned)

def parse_line(line, form_data, key_map):
    line = normalize(line)

    if ":" in line:
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        resolved = resolve_key(key, key_map)
        if resolved:
            return resolved, value

    # missing colon case
    line_lower = line.lower()

    for norm_key, original_key in key_map.items():
        if line_lower.startswith(norm_key):
            value = line[len(norm_key):].strip()
            return original_key, value

    return None, None

form_data = {
    "Registration No": "",
    "Date": "",
    "Name": "",
    "Guardian Name": "",
    "Relationship with Guardian": "",
    # "Age": "",
    "Gender": "",
    "Marital Status": "",
    "No. of Children": "",
    # "Religion": "",
    # "Maslak": "",
    # "Kya aap Milaad/Nazr Niyaz/Fateha maantay hain?": "",
    # "Caste": "",
    # "Mother Tongue": "",
    # "Height": "",
    # "Complexion": "",
    # "Any Physical Illness": "",
    # "Any Physical Disability": "",
    # "Qualification": "",
    # "Job & Profession": "",
    # "Monthly Income": "",
    # "Girl/Woman: Ghar ka kya kya kaam aata hai?": "",
    # "Your Current City": "",
    # "State/Province": "",
    # "Country": "",
    # "Nationality/Visa Status": "",
    # "In Pakistan from which city you belongs to": "",
    # "About Father": "",
    # "About Mother": "",
    # "About Sisters": "",
    # "About Brothers": "",
    # "About Your Personality": "",
    # "About Your Hobby": "",
    # "Any other detail": "",
    # "About your Home: Size? Own/Rent?": "",
    # "Your Living Standard": "",
    # "Your Social Class": "",
    # "Your Requirements in Detail": "",
    # "Requirements Marital Status": "",
    # "Requirements Age": "",
    # "Requirements Qualification": "",
    # "Requirements Caste": "",
    # "Requirements Height": "",
    # "Requirements City & Country": "",
    # "Requirements Other details": "",
    # "Profile Posted By": ""
}



print("Paste the form. Press Ctrl+D (Linux/macOS) or Ctrl+Z then Enter (Windows).\n")

in_requirements = False
key_map = {normalize_key(k): k for k in form_data.keys()}

for line in sys.stdin:
    key, value = parse_line(line, form_data, key_map)

    if key is None:
        continue

    # form_data[key] = value

    # Everything after this belongs to the Requirements section
    if key == "Your Requirements in Detail":
        in_requirements = True

    # Rename duplicate keys inside the requirements section
    if in_requirements:
        if key == "Marital Status":
            key = "Requirements Marital Status"
        elif key == "Age":
            key = "Requirements Age"
        elif key == "Qualification":
            key = "Requirements Qualification"
        elif key == "Caste":
            key = "Requirements Caste"
        elif key == "Height":
            key = "Requirements Height"
        elif key == "City & Country":
            key = "Requirements City & Country"
        elif key == "Other details":
            key = "Requirements Other details"

    if key in form_data:
        form_data[key] = value
    else:
        print(f"Warning: Unknown field '{key}'")

print("\nParsed Data:\n")

# for key, value in form_data.items():
#     print(f"{key}: {value}")

print(form_data)

 


'''
Registration Form

Registration No: next
line
line Religion: started the field right after finishing the previous field withou \n
Date missing semi-colon DONE
NAmE: capitalized DONE
Guardian Name%: special character DONE
aa: unknown field but with colon DONE
Gender: field out of order DONE
No.. of. Children: missing or additional period DONE
Relationship with Gardian: misspelling
Marital Statsu: jumbled spelling

Age: 21
Gender:
Marital Status:
No of Children:

Religion:
Maslak
Kya aap Milaad/Nazr Niyaz/Fateha maantay hain?:
Caste:
Mother Tongue:

Height:
Complexion:
Any Physical Illness:
Any Physical Disability:

Qualification
Job & Profession
Monthly Income
Girl/Woman: Ghar ka kya kya kaam aata hai?

Your Current City:
State/Province:
Country:
Nationality/Visa Status:
In Pakistan from which city you belongs to:

About Father:
About Mother:
About Sisters:
About Brothers:

About Your Personality:
About Your Hobby:
Any other detail:

About your Home: Size? Own/Rent?:
Your Living Standard:
Your Social Class:

Your Requirements in Detail:
Marital Status :
Age :
Qualification :
Caste :
Height
City & Country :
Other details :
Profile Posted By: 

Divorce/Khula Candidate
Kya aap ke paas Divorce/Khula certificate hai?:

2nd Marriage & 2nd Wife:
Female: Kya aap First wife ki mojoodgi mei 2nd wife banney ko tayyar hain?:
Male: 
Sawal. Aap First wife ki mojoodgi mei 2nd marriage kiyun kerna chahtay hain? 
Sawal: Ky aap ke paas 2nd marriage ke liye Govt Permission hai?


***Registration Form****
'''
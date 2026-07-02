from parser import parse_form
import json

s = "Name: John Doe\nAge: 30\nAbout Your Personality: kind\\nlover of cats\nMarital Status: Single\nAbout Your Personality: continues on next line\n"
lines = s.splitlines(True)
print('INPUT LINES:')
print(lines)
parsed = parse_form(lines)
print('\nPARSED:')
print(json.dumps(parsed, indent=2, ensure_ascii=False))

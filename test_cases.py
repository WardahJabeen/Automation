from parser import parse_form
import json

cases = [
    ("Case 1",
     "date: aa\naa Name: name\n"),
    ("Case 2",
     "date: type: monthly\nname: first name: hi last name: bye\n"),
    ("Case 3",
     "name: first\nname: last\n"),
]

for title, s in cases:
    print(title)
    lines = s.splitlines(True)
    parsed = parse_form(lines)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    print('\n' + ('-'*40) + '\n')

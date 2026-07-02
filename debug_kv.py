from parser import find_key_value_pairs, parse_form

line = "name: first name: hi last name: bye\n"
from form_fields import build_key_map
km = build_key_map()
print('LINE:', line)
print('PAIRS:', find_key_value_pairs(line, km))
print('\nFULL PARSE:')
print(parse_form([line]))

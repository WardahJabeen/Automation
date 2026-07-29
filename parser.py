import argparse
import json
import re
import sys
from db import Database

try:
    import mysql.connector
except ImportError:
    mysql = None


from form_fields import (
    SECTION_HEADER,
    REQUIREMENT_DUPLICATE_FIELDS,
    build_key_map,
    get_default_form_data,
    resolve_key,
    normalize_key,
)
 
def normalize_text(text):
    text = text.strip()
    text = re.sub(r"[^a-zA-Z0-9: /?&\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_separator_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and all(ch == "*" for ch in stripped)


def split_ordered_list_items(value: str):
    if value is None:
        return []
    value = value.strip()
    if not value:
        return []

    parts = re.split(r'(?:(?<=\n)|^)\s*\d+\.\s*', value)
    if len(parts) <= 1:
        return [value]

    items = [part.strip() for part in parts if part.strip() != ""]
    if not items:
        return [""]
    return items


def append_form_value(form_data, key, value):
    value = clean_field_value(key, value)
    if isinstance(form_data.get(key), list):
        items = split_ordered_list_items(value)
        for item in items:
            if item != "":
                form_data[key].append(sanitize_value(item))
            else:
                form_data[key].append("")
        return

    existing = form_data.get(key, "")
    newval = sanitize_value(value)
    if existing:
        label = normalize_key(key)
        form_data[key] = f"{existing}, {label}: {newval}"
    else:
        form_data[key] = newval


def append_continuation(form_data, key, append):
    if append is None or append == "":
        return

    if isinstance(form_data.get(key), list):
        ordered_match = re.match(r'^\s*\d+\.\s*(.*)$', append)
        if ordered_match:
            form_data[key].append(sanitize_value(ordered_match.group(1)))
            return

        if form_data[key]:
            form_data[key][-1] = sanitize_value(f"{form_data[key][-1]} {append}")
        else:
            form_data[key].append(sanitize_value(append))
        return

    existing = form_data.get(key, "")
    combined = (existing + " " + append) if existing else append
    form_data[key] = sanitize_value(combined)


def clean_field_value(key, value):
    if value is None:
        return value
    if key == "WhatsApp No":
        value = re.sub(r"\s*registration\s+form\s*$", "", value, flags=re.IGNORECASE)
    return value


def sanitize_value(value: str) -> str:
    """Remove escaped and actual newlines from stored values and collapse whitespace."""
    if value is None:
        return ""
    # remove literal backslash-n sequences and any CR/LF/newline characters
    v = value.replace('\\n', ' ').replace('\\r\\n', ' ').replace('\r', ' ').replace('\n', ' ')
    # collapse multiple whitespace
    v = re.sub(r"\s+", " ", v).strip()
    return v


def parse_line(line, key_map):
    raw = line.strip()
    if not raw:
        return None, None

    cleaned = normalize_text(raw)
    if ":" in cleaned:
        key_part, value_part = cleaned.split(":", 1)
        key = resolve_key(key_part, key_map)
        if key:
            return key, value_part.strip()

    normalized = re.sub(r"[^a-z0-9 ]+", "", cleaned.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    if not normalized:
        return None, None

    if normalized in key_map:
        return key_map[normalized], None

    for norm_key, canonical_key in key_map.items():
        if normalized.startswith(f"{norm_key} "):
            remainder = normalized[len(norm_key) :].strip()
            return canonical_key, remainder

    return None, None


def find_key_value_pairs(line, key_map, max_candidate_len=60):
    """Return list of (key, value) pairs found on a single line.

    Strategy: scan colon positions and attempt to find a preceding substring that
    normalizes to a known key by trying start positions within a window. Prefer
    the longest matching candidate for accuracy.
    """
    pairs = []
    colons = [m.start() for m in re.finditer(':', line)]
    if not colons:
        return [], ""

    boundaries = []  # tuples (start_index, colon_index, resolved_key)
    for c in colons:
        start_window = max(0, c - max_candidate_len)
        best = None
        best_norm = None
        best_start = None
        # try longer candidates first
        for start in range(start_window, c):
            # avoid candidates that include another colon (would span prior key:value)
            if ':' in line[start:c]:
                continue
            candidate = line[start:c].strip()
            if not candidate:
                continue
            # prefer exact normalized matches for boundaries (avoid fuzzy matches inside values)
            nk = normalize_key(candidate)
            if nk in key_map:
                # look for a previous token immediately before candidate
                # find the previous word token (skip spaces first)
                j = start - 1
                # skip whitespace
                while j >= 0 and line[j].isspace():
                    j -= 1
                end = j
                while j >= 0 and line[j].isalnum():
                    j -= 1
                prev_token = line[j+1:end+1].strip() if end >= 0 else ""

                # if there's a long previous token (likely part of a phrase), only accept
                # this candidate if the combined phrase is a known key; allow short tokens
                if prev_token and len(prev_token) > 2:
                    combined_nk = normalize_key(prev_token + " " + candidate)
                    if combined_nk not in key_map:
                        continue

                resolved = key_map[nk]
                if best is None or len(candidate) > len(best):
                    best = candidate
                    best_norm = resolved
                    best_start = start
        if best is not None:
            boundaries.append((best_start, c, best_norm))

    if not boundaries:
        return pairs, ""

    # sort boundaries by start index
    boundaries.sort(key=lambda x: x[0])

    for idx, (start, colon_idx, resolved_key) in enumerate(boundaries):
        value_start = colon_idx + 1
        if idx + 1 < len(boundaries):
            next_start = boundaries[idx + 1][0]
            value = line[value_start:next_start].strip()
        else:
            value = line[value_start:].strip()

        pairs.append((resolved_key, value if value != "" else None))

    # any leading text before the first detected key boundary
    first_start = boundaries[0][0] if boundaries else 0
    leading = line[:first_start].strip()

    return pairs, leading


def parse_form(lines):
    # Normalize literal "\n" sequences inside the input so that
    # values containing escaped newlines are treated as separate logical lines.
    content = "".join(lines)
    # Replace literal backslash-newline sequences (both \r\n and \n)
    content = content.replace('\\r\\n', '\n').replace('\\n', '\n')
    expanded_lines = content.splitlines()

    key_map = build_key_map()
    form_data = get_default_form_data()
    seen_keys = set()
    pending_key = None
    in_requirements = False
    last_key = None
    summary_mode = False
    summary_lines = []

    i = 0
    while i < len(expanded_lines):
        raw_line = expanded_lines[i]
        line = raw_line.rstrip("\n")
        i += 1

        if is_separator_line(line):
            summary_mode = True
            continue

        if summary_mode:
            key, value = parse_line(line, key_map)
            if key == "Rishta Given":
                if summary_lines:
                    form_data["Summary"] = sanitize_value(" ".join(summary_lines))
                    seen_keys.add("Summary")
                    summary_lines = []
                summary_mode = False
            else:
                if line.strip():
                    summary_lines.append(line.strip())
                continue

        if not line.strip():
            continue

        # First, try to extract multiple key:value pairs that may exist on the same line
        pairs, leading = find_key_value_pairs(line, key_map)
        if pairs:
            # print(f"DEBUG: Processing line: {line}")
            # if there's leading text before the first key, treat it as continuation
            if leading and last_key is not None:
                existing = form_data.get(last_key, "")
                combined = (existing + " " + leading) if existing else leading
                form_data[last_key] = sanitize_value(combined)
           
                

            for k, v in pairs:
                
                if k == SECTION_HEADER:
                    seen_keys.add(SECTION_HEADER)
                    in_requirements = True
                    if v:
                        existing = form_data.get(SECTION_HEADER, "")
                        newval = sanitize_value(v)
                        form_data[SECTION_HEADER] = (existing + " " + newval) if existing else newval
                        last_key = SECTION_HEADER
                    continue

                if in_requirements and k in REQUIREMENT_DUPLICATE_FIELDS:
                    k = REQUIREMENT_DUPLICATE_FIELDS[k]

                if v is None:
                    pending_key = k
                    seen_keys.add(k)
                    last_key = k
                    continue

                seen_keys.add(k)
                append_form_value(form_data, k, v)
                last_key = k

            continue


        # print(f"DEBUG 2: Processing line: {line}")


        # Fallback to single-key parsing
        key, value = parse_line(line, key_map)


        # If there was a pending key (key on previous line with value on this line)
        if pending_key is not None:
            if key is None:
                # Treat this line as the value for the pending key (append if exists)
                seen_keys.add(pending_key)
                append_form_value(form_data, pending_key, line.strip())
                last_key = pending_key
                pending_key = None
                continue
            # If this line started a new key, set empty value for pending_key
            form_data[pending_key] = ""

            pending_key = None

        # If no key detected on this line, treat it as continuation of last filled key
        if key is None:
            if last_key == "WhatsApp No" and re.fullmatch(r"\s*registration\s+form\s*", line, re.IGNORECASE):
                continue
            if last_key is not None:
                # append as continuation of the last key's value (store without literal newlines)
                append_continuation(form_data, last_key, line.strip())
            continue

        # Section header starts special requirements mapping
        if key == SECTION_HEADER:
            seen_keys.add(SECTION_HEADER)
            in_requirements = True
            if value:
                existing = form_data.get(SECTION_HEADER, "")
                newval = sanitize_value(value)
                form_data[SECTION_HEADER] = (existing + " " + newval) if existing else newval
                last_key = SECTION_HEADER
            continue

        # Remap duplicate requirement fields when inside requirements section
        if in_requirements and key in REQUIREMENT_DUPLICATE_FIELDS:
            key = REQUIREMENT_DUPLICATE_FIELDS[key]

            
        # If value is None then the next non-empty line is the value
        if value is None:
            pending_key = key
            seen_keys.add(key)
            last_key = key
            continue


        # Otherwise append the value to existing (to collect duplicates) and remember last key
        seen_keys.add(key)
        append_form_value(form_data, key, value)
        last_key = key

    if pending_key is not None:
        form_data[pending_key] = ""

    if summary_mode and summary_lines:
        form_data["Summary"] = sanitize_value(" ".join(summary_lines))
        seen_keys.add("Summary")

    # print("DEBUG: Key Map:", key_map)

    return form_data, seen_keys


def field_label_to_db_column(label):
    label = re.sub(r"[^a-zA-Z0-9 ]+", " ", label).strip().lower()
    return re.sub(r"\s+", "_", label)


def insert_into_mysql(form_data, host, user, password, database, table):
    if mysql is None:
        raise ImportError(
            "mysql.connector is required to insert into MySQL. Install mysql-connector-python."
        )

    columns = []
    values = []

    for label, value in form_data.items():
        if value != "":
            columns.append(field_label_to_db_column(label))
            values.append(value)

    if not columns:
        raise ValueError("No data to insert into MySQL.")

    quoted_columns = ", ".join([f"`{col}`" for col in columns])
    placeholders = ", ".join(["%s"] * len(values))
    query = f"INSERT INTO `{table}` ({quoted_columns}) VALUES ({placeholders})"

    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        use_pure=True,
    )
    cursor = connection.cursor()
    cursor.execute(query, values)
    connection.commit()
    rowcount = cursor.rowcount
    cursor.close()
    connection.close()
    return rowcount


# def read_input(file_path=None):
#     if file_path:
#         with open(file_path, "r", encoding="utf-8") as handle:
#             return handle.readlines()
#     return sys.stdin.readlines()


def read_input(file_path=None):
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.readlines()

    return sys.stdin.readlines()


def main():
    parser = argparse.ArgumentParser(
        description="Parse a text form from stdin or a file and optionally insert it into MySQL."
    )
    parser.add_argument("--file", "-f", help="Read the form from a file instead of stdin.")
    parser.add_argument("--json", action="store_true", help="Print parsed data as JSON.")
    parser.add_argument("--missing-fields", action="store_true", help="Print expected fields that were not mentioned in the submitted form.")
    parser.add_argument("--mysql-host", help="MySQL host for insertion.")
    parser.add_argument("--mysql-user", help="MySQL username.")
    parser.add_argument("--mysql-password", help="MySQL password.")
    parser.add_argument("--mysql-database", help="MySQL database name.")
    parser.add_argument("--mysql-table", help="MySQL table name.")
    args = parser.parse_args()

    lines = read_input(args.file)

    parsed, seen_keys = parse_form(lines)

    if args.json:
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    else:
        print(parsed)

    missing = [key for key in parsed.keys() if key not in seen_keys]
    print("\nMissing expected fields:")
    if missing:
        for key in missing:
            print(f"{key}, ", end="")
    else:
        print("(none)")
    db = Database()
    db.insert_form(parsed)
    db.close()

    if args.mysql_table:
        if not all([args.mysql_host, args.mysql_user, args.mysql_password, args.mysql_database]):
            parser.error(
                "--mysql-table requires --mysql-host, --mysql-user, --mysql-password, and --mysql-database."
            )
        row_count = insert_into_mysql(
            parsed,
            host=args.mysql_host,
            user=args.mysql_user,
            password=args.mysql_password,
            database=args.mysql_database,
            table=args.mysql_table,
        )
        print(f"Inserted {row_count} row(s) into {args.mysql_table}.")


if __name__ == "__main__":
    main()

import json
import psycopg

class Database:
    def __init__(self):
        self.conn = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user="postgres",
            password="password"
        )

    def insert_form(self, form_data):
        columns = ', '.join(f'"{k}"' for k in form_data.keys())
        placeholders = ', '.join(['%s'] * len(form_data))

        values = [json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for v in form_data.values()]

        query = f"""
        INSERT INTO registration_forms ({columns})
        VALUES ({placeholders})
        """

        with self.conn.cursor() as cur:
            cur.execute(query, values)

        self.conn.commit()

    def append_rishta_given(self, phone_number, rishta_items):
        if not rishta_items:
            return

        with self.conn.cursor() as cur:
            cur.execute('SELECT "Rishta Given" FROM registration_forms WHERE "WhatsApp No" = %s', [phone_number])
            row = cur.fetchone()

            if row:
                existing = row[0]
                if existing is None:
                    combined = rishta_items
                elif isinstance(existing, list):
                    combined = existing + rishta_items
                else:
                    try:
                        existing_parsed = json.loads(existing)
                    except (TypeError, ValueError):
                        existing_parsed = [existing]
                    if isinstance(existing_parsed, list):
                        combined = existing_parsed + rishta_items
                    else:
                        combined = [existing_parsed] + rishta_items

                cur.execute(
                    'UPDATE registration_forms SET "Rishta Given" = %s WHERE "WhatsApp No" = %s',
                    [json.dumps(combined, ensure_ascii=False), phone_number],
                )
            else:
                cur.execute(
                    'INSERT INTO registration_forms ("WhatsApp No", "Rishta Given") VALUES (%s, %s)',
                    [phone_number, json.dumps(rishta_items, ensure_ascii=False)],
                )

        self.conn.commit()

    def save_summary(self, phone_number, summary_text, append=False):
        with self.conn.cursor() as cur:
            cur.execute('SELECT "Summary" FROM registration_forms WHERE "WhatsApp No" = %s', [phone_number])
            row = cur.fetchone()
            if row:
                existing_summary = row[0]
                if append and existing_summary:
                    summary_text = f"{existing_summary} {summary_text}"
                cur.execute(
                    'UPDATE registration_forms SET "Summary" = %s WHERE "WhatsApp No" = %s',
                    [summary_text, phone_number],
                )
            else:
                cur.execute(
                    'INSERT INTO registration_forms ("WhatsApp No", "Summary") VALUES (%s, %s)',
                    [phone_number, summary_text],
                )

        self.conn.commit()

    def update_summary(self, phone_number, summary_text):
        self.save_summary(phone_number, summary_text, append=False)

    def get_profile(self, phone_number):
        with self.conn.cursor() as cur:
            cur.execute('SELECT * FROM registration_forms WHERE "WhatsApp No" = %s', [phone_number])
            row = cur.fetchone()
            if not row:
                return None
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))

    def get_summary(self, phone_number):
        with self.conn.cursor() as cur:
            cur.execute('SELECT "Summary" FROM registration_forms WHERE "WhatsApp No" = %s', [phone_number])
            row = cur.fetchone()
            return row[0] if row else None

    def whatsapp_no_exists(self, phone_number):
        with self.conn.cursor() as cur:
            cur.execute('SELECT 1 FROM registration_forms WHERE "WhatsApp No" = %s', [phone_number])
            return cur.fetchone() is not None

    def get_matching(self, field_label, value):
        """Return list of rows (as dicts) where column `field_label` ILIKE the given value.

        `field_label` must be a simple column label (letters, numbers, spaces, underscore, dash, parens).
        """
        import re

        if not field_label or not isinstance(field_label, str):
            raise ValueError("field_label must be a non-empty string")

        # simple whitelist to avoid SQL injection via column name
        if not re.match(r'^[A-Za-z0-9 _\-\(\)]+$', field_label):
            raise ValueError("Invalid field label")

        pattern = f"%{value}%" if value is not None else "%"
        query = f'SELECT * FROM registration_forms WHERE "{field_label}" ILIKE %s'

        with self.conn.cursor() as cur:
            cur.execute(query, [pattern])
            rows = cur.fetchall()
            if not rows:
                return []
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]

    def close(self):
        self.conn.close()
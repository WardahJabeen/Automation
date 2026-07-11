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

        query = f"""
        INSERT INTO registration_forms ({columns})
        VALUES ({placeholders})
        """

        with self.conn.cursor() as cur:
            cur.execute(query, list(form_data.values()))

        self.conn.commit()

    def close(self):
        self.conn.close()
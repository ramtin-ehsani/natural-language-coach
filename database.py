import sqlite3


class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        c = self.conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS texts(id INTEGER PRIMARY KEY, user_id INTEGER not null, username TEXT not null, text TEXT, role TEXT);"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS fitbit(user_id INTEGER PRIMARY KEY, access_token TEXT not null, refresh_token TEXT not null, expires_at TEXT not null, client_id TEXT not null, client_secret TEXT not null, fitbit_id TEXT not null);"
        )

    def select(self, sql, parameters=[]):
        c = self.conn.cursor()
        c.execute(sql, parameters)
        return c.fetchall()

    def execute(self, sql, parameters=[]):
        c = self.conn.cursor()
        c.execute(sql, parameters)
        self.conn.commit()
        return c.lastrowid

    def close(self):
        self.conn.close()

    def create_fitbit_details(self, user_id, access_token, refresh_token, expires_at, client_id, client_secret, fitbit_id):
        return self.execute(
            "INSERT INTO fitbit (user_id, access_token, refresh_token, expires_at, client_id, client_secret, fitbit_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [user_id, access_token, refresh_token, expires_at, client_id, client_secret, fitbit_id],
        )

    def get_fitbit_details(self, user_id):
        data = self.select("SELECT * FROM fitbit WHERE user_id = ?;", [user_id])
        if data:
            d = data[0]
            retval = {
                "user_id": d[0],
                "access_token": d[1],
                "refresh_token": d[2],
                "expires_at": d[3],
                "client_id": d[4],
                "client_secret": d[5],
                "fitbit_id": d[6]
            }
            return retval
        else:
            return None

    def update_tokens(self, user_id, access_token, refresh_token, expires_at):
        return self.execute(
            "UPDATE fitbit SET access_token = ?, refresh_token = ?, expires_at = ?  WHERE user_id = ?;",
            [user_id, access_token, refresh_token, expires_at]
        )

    def insert_text(self, user_id, username, text, role):
        return self.execute(
            "INSERT INTO texts (user_id, username, text, role) VALUES (?, ?, ?, ?)",
            [user_id, username, text, role],
        )

    def get_user_texts(self, user_id):
        data = self.select("SELECT * FROM texts WHERE user_id = ?;", [user_id])
        texts = []
        for d in data:
            retval = {
                "user_id": d[1],
                "username": d[2],
                "text": d[3],
                "role": d[4],
            }
            texts.append(retval)
        return texts

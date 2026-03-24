from database import get_db


class User:
    def __init__(self, id, username, email, password_hash, created_at, updated_at):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def create(username, email, password_hash):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        db.commit()
        return User.get_by_id(cursor.lastrowid)

    @staticmethod
    def get_by_id(user_id):
        row = (
            get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))

    @staticmethod
    def get_all():
        rows = get_db().execute("SELECT * FROM users ORDER BY id").fetchall()
        return [User(**dict(row)) for row in rows]

    @staticmethod
    def update(user_id, **kwargs):
        allowed = {"username", "email", "password_hash"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return User.get_by_id(user_id)
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]
        db = get_db()
        db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        db.commit()
        return User.get_by_id(user_id)

    @staticmethod
    def delete(user_id):
        db = get_db()
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()

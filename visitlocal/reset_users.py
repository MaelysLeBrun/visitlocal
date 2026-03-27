from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# comptes propres
users = [
    ("Admin", "admin@test.com", generate_password_hash("admin123"), "admin"),
    ("User", "user@test.com", generate_password_hash("user123"), "user")
]

for user in users:
    cursor.execute(
        "INSERT INTO users (nom, email, mot_de_passe, role) VALUES (?, ?, ?, ?)",
        user
    )

conn.commit()
conn.close()

print("✔️ Utilisateurs recréés")

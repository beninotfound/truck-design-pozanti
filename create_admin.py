# -*- coding: utf-8 -*-
"""
create_admin.py
-------------------------------------------------------
İlk (veya ek) admin hesabını oluşturmak için kullanılır.
Şifre asla düz metin olarak saklanmaz; werkzeug generate_password_hash
ile güvenli şekilde hashlenir (PBKDF2/scrypt tabanlı, salt içerir).

Kullanım:
    python create_admin.py
-------------------------------------------------------
"""
import getpass
import sys
from werkzeug.security import generate_password_hash

from db import get_db, init_db, now_str


def main():
    init_db()

    username = input("Admin kullanıcı adı: ").strip()
    if not username:
        print("Kullanıcı adı boş olamaz.")
        sys.exit(1)

    password = getpass.getpass("Admin şifresi: ")
    password2 = getpass.getpass("Admin şifresi (tekrar): ")

    if password != password2:
        print("Şifreler eşleşmiyor.")
        sys.exit(1)

    if len(password) < 8:
        print("Şifre en az 8 karakter olmalıdır.")
        sys.exit(1)

    password_hash = generate_password_hash(password)

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (password_hash, username),
        )
        conn.commit()
        conn.close()
        print(f"'{username}' kullanıcısının şifresi güncellendi.")
    else:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, now_str()),
        )
        conn.commit()
        conn.close()
        print(f"Admin hesabı '{username}' başarıyla oluşturuldu.")


if __name__ == "__main__":
    main()

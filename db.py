"""
db.py
-------------------------------------------------------
Truck Design Pozantı - SQLite veritabanı katmanı.

Tüm sorgular parametreli (?) çalışır -> SQL injection'a karşı korumalı.
Hiçbir yerde kullanıcı girdisi string birleştirme ile sorguya eklenmez.
-------------------------------------------------------
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_db():
    """Yeni bir sqlite3 bağlantısı döndürür (satırlar dict gibi erişilebilir)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Veritabanı ve tablolar yoksa oluşturur. Uygulama her başladığında çağrılır."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS slides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            image TEXT,
            button_text TEXT,
            button_link TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # visit_date + ip_hash birlikte UNIQUE -> aynı ziyaretçi aynı gün
    # birden fazla kez sayılmaz (refresh ile şişirmeyi engeller).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(ip_hash, visit_date)
        )
    """)

    # Ürün / stok yönetimi - admin paneli içindeki "Excel benzeri" tablo için.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stok_kodu TEXT UNIQUE NOT NULL,
            ad TEXT NOT NULL,
            adet INTEGER NOT NULL DEFAULT 0,
            gelis_fiyati REAL NOT NULL DEFAULT 0,
            satis_fiyati REAL NOT NULL DEFAULT 0,
            kdv_orani REAL NOT NULL DEFAULT 20,
            image TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            attempted_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

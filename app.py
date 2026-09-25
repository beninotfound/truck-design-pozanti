# -*- coding: utf-8 -*-
"""
app.py
-------------------------------------------------------
TRUCK DESIGN POZANTI - Ana Flask Uygulaması

Güvenlik önlemleri (özet):
  - SQL Injection: tüm sorgular parametreli (?) -> db.py
  - XSS: Jinja2 autoescape açık, |safe kullanılmıyor
  - CSRF: Flask-WTF CSRFProtect tüm POST formlarında aktif
  - Password hashing: werkzeug generate_password_hash / check_password_hash
  - Güvenli dosya upload: security.py (uzantı beyaz listesi, uuid isimlendirme,
    Pillow ile gerçek görsel doğrulama, boyut limiti)
  - Path traversal: secure_filename + commonpath kontrolü
  - Session security: HttpOnly, SameSite, (prod'da) Secure cookie
  - Basit brute-force koruması: login denemesi IP bazlı sınırlandırılır
  - Admin endpointleri login_required ile korunur
-------------------------------------------------------
"""
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, send_from_directory
)
from werkzeug.security import check_password_hash
from flask_wtf import CSRFProtect
from dotenv import load_dotenv

from db import get_db, init_db, now_str, today_str
from security import save_uploaded_image, delete_uploaded_image, hash_ip, get_client_ip

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

app = Flask(__name__)

# ====== TEMEL AYARLAR ======
# SECRET_KEY .env'den okunur; yoksa (sadece geliştirme için) rastgele üretilir.
# Prod'da mutlaka .env içinde sabit bir SECRET_KEY tanımlanmalı, aksi halde
# uygulama her yeniden başladığında tüm oturumlar geçersiz olur.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB dosya yükleme limiti

FLASK_ENV = os.environ.get("FLASK_ENV", "production")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = FLASK_ENV == "production"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# CSRF koruması - tüm POST formlarında {{ csrf_token() }} kullanılmalı
csrf = CSRFProtect(app)

# WhatsApp numarası - tek yerden değiştirilebilir
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "905xxxxxxxxx")

SITE_NAME = "Truck Design Pozantı"

# Basit brute-force koruması: aynı IP, LOGIN_WINDOW_MIN dakika içinde
# LOGIN_MAX_ATTEMPTS'den fazla başarısız giriş yaparsa geçici olarak kilitlenir.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_MIN = 10


# ====== JINJA GLOBALS ======
@app.context_processor
def inject_globals():
    return {
        "WHATSAPP_NUMBER": WHATSAPP_NUMBER,
        "SITE_NAME": SITE_NAME,
        "current_year": datetime.utcnow().year,
    }


# ====== ADMIN GİRİŞ DEKORATÖRÜ ======
def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Lütfen önce giriş yapın.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped


# ====== ZİYARETÇİ SAYACI (her istekten önce, sadece sayfa görüntülemelerinde) ======
@app.before_request
def track_visit():
    # Statik dosyalar ve admin alanı sayaca dahil edilmesin
    if request.endpoint in ("static",) or (request.path or "").startswith("/admin"):
        return
    try:
        ip_hash = hash_ip(get_client_ip(request), app.config["SECRET_KEY"])
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO visits (ip_hash, visit_date, created_at) VALUES (?, ?, ?)",
            (ip_hash, today_str(), now_str()),
        )
        conn.commit()
        conn.close()
    except Exception:
        # Ziyaret sayacı hatası sitenin çalışmasını asla engellememeli
        pass


# ====== HALKA AÇIK SAYFALAR ======
@app.route("/")
def index():
    conn = get_db()
    posts = conn.execute(
        "SELECT * FROM posts ORDER BY datetime(created_at) DESC LIMIT 6"
    ).fetchall()
    slides = conn.execute(
        "SELECT * FROM slides ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    conn.close()
    return render_template("index.html", posts=posts, slides=slides)


@app.route("/hizmetler")
def hizmetler():
    return render_template("hizmetler.html")


@app.route("/galeri")
def galeri():
    conn = get_db()
    posts = conn.execute(
        "SELECT * FROM posts ORDER BY datetime(created_at) DESC"
    ).fetchall()
    conn.close()
    return render_template("galeri.html", posts=posts)


@app.route("/hakkimizda")
def hakkimizda():
    return render_template("hakkimizda.html")


@app.route("/iletisim", methods=["GET", "POST"])
def iletisim():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()

        errors = []
        if not name:
            errors.append("Ad Soyad zorunludur.")
        if not email:
            errors.append("E-posta zorunludur.")
        if not message:
            errors.append("Mesaj zorunludur.")
        if len(name) > 150 or len(email) > 150 or len(phone) > 50:
            errors.append("Girilen bilgiler çok uzun.")
        if len(message) > 5000:
            errors.append("Mesaj çok uzun.")

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("iletisim"))

        conn = get_db()
        conn.execute(
            "INSERT INTO messages (name, phone, email, message, is_read, created_at) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            (name, phone, email, message, now_str()),
        )
        conn.commit()
        conn.close()
        flash("Mesajınız başarıyla gönderildi. En kısa sürede dönüş yapacağız.", "success")
        return redirect(url_for("iletisim"))

    return render_template("iletisim.html")


# ====== ADMIN - GİRİŞ / ÇIKIŞ ======
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        ip_hash = hash_ip(get_client_ip(request), app.config["SECRET_KEY"])
        conn = get_db()

        cutoff = (datetime.utcnow() - timedelta(minutes=LOGIN_WINDOW_MIN)).strftime("%Y-%m-%d %H:%M:%S")
        recent_attempts = conn.execute(
            "SELECT COUNT(*) AS c FROM login_attempts WHERE ip_hash = ? AND attempted_at > ?",
            (ip_hash, cutoff),
        ).fetchone()["c"]

        if recent_attempts >= LOGIN_MAX_ATTEMPTS:
            conn.close()
            flash("Çok fazla başarısız giriş denemesi. Lütfen birkaç dakika sonra tekrar deneyin.", "error")
            return render_template("admin_login.html"), 429

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            conn.execute("DELETE FROM login_attempts WHERE ip_hash = ?", (ip_hash,))
            conn.commit()
            conn.close()
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = user["username"]
            session.permanent = True
            flash("Giriş başarılı, hoş geldiniz!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            conn.execute(
                "INSERT INTO login_attempts (ip_hash, attempted_at) VALUES (?, ?)",
                (ip_hash, now_str()),
            )
            conn.commit()
            conn.close()
            # Kullanıcı adı yanlış mı şifre yanlış mı belirtilmiyor (enumeration engelleme)
            flash("Kullanıcı adı veya şifre hatalı.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for("admin_login"))


# ====== ADMIN - DASHBOARD ======
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    posts = conn.execute("SELECT * FROM posts ORDER BY datetime(created_at) DESC").fetchall()
    slides = conn.execute("SELECT * FROM slides ORDER BY sort_order ASC, id ASC").fetchall()
    messages = conn.execute("SELECT * FROM messages ORDER BY datetime(created_at) DESC").fetchall()

    total_posts = conn.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"]
    total_slides = conn.execute("SELECT COUNT(*) AS c FROM slides").fetchone()["c"]
    total_messages = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
    unread_messages = conn.execute("SELECT COUNT(*) AS c FROM messages WHERE is_read = 0").fetchone()["c"]
    total_visits = conn.execute("SELECT COUNT(*) AS c FROM visits").fetchone()["c"]
    today_visits = conn.execute(
        "SELECT COUNT(*) AS c FROM visits WHERE visit_date = ?", (today_str(),)
    ).fetchone()["c"]
    total_products = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    low_stock_products = conn.execute("SELECT COUNT(*) AS c FROM products WHERE adet <= 5").fetchone()["c"]
    conn.close()

    stats = {
        "total_posts": total_posts,
        "total_slides": total_slides,
        "total_messages": total_messages,
        "unread_messages": unread_messages,
        "total_visits": total_visits,
        "today_visits": today_visits,
        "total_products": total_products,
        "low_stock_products": low_stock_products,
    }
    return render_template("admin.html", posts=posts, slides=slides, messages=messages, stats=stats)


# ====== ADMIN - GÖNDERİLER (POSTS) ======
@app.route("/admin/posts/create", methods=["GET", "POST"])
@admin_required
def create_post():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()

        if not title or not content:
            flash("Başlık ve açıklama zorunludur.", "error")
            return render_template("create_post.html")

        image_filename = ""
        file = request.files.get("image")
        if file and file.filename:
            ok, result = save_uploaded_image(file, app.config["UPLOAD_FOLDER"])
            if not ok:
                flash(result, "error")
                return render_template("create_post.html")
            image_filename = result

        conn = get_db()
        conn.execute(
            "INSERT INTO posts (title, content, image, created_at) VALUES (?, ?, ?, ?)",
            (title, content, image_filename, now_str()),
        )
        conn.commit()
        conn.close()
        flash("Gönderi başarıyla eklendi.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_post.html")


@app.route("/admin/posts/<int:post_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()

        if not title or not content:
            flash("Başlık ve açıklama zorunludur.", "error")
            conn.close()
            return render_template("edit_post.html", post=post)

        image_filename = post["image"]
        file = request.files.get("image")
        if file and file.filename:
            ok, result = save_uploaded_image(file, app.config["UPLOAD_FOLDER"])
            if not ok:
                flash(result, "error")
                conn.close()
                return render_template("edit_post.html", post=post)
            # Eski görseli sil, yenisini ata
            delete_uploaded_image(post["image"], app.config["UPLOAD_FOLDER"])
            image_filename = result

        conn.execute(
            "UPDATE posts SET title = ?, content = ?, image = ? WHERE id = ?",
            (title, content, image_filename, post_id),
        )
        conn.commit()
        conn.close()
        flash("Gönderi güncellendi.", "success")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("edit_post.html", post=post)


@app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@admin_required
def delete_post(post_id):
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post is None:
        conn.close()
        abort(404)
    delete_uploaded_image(post["image"], app.config["UPLOAD_FOLDER"])
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    flash("Gönderi silindi.", "success")
    return redirect(url_for("admin_dashboard"))


# ====== ADMIN - SLIDER ======
@app.route("/admin/slides/create", methods=["GET", "POST"])
@admin_required
def create_slide():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        button_text = (request.form.get("button_text") or "").strip()
        button_link = (request.form.get("button_link") or "").strip()
        try:
            sort_order = int(request.form.get("sort_order") or 0)
        except ValueError:
            sort_order = 0

        if not title:
            flash("Başlık zorunludur.", "error")
            return render_template("create_slide.html")

        image_filename = ""
        file = request.files.get("image")
        if file and file.filename:
            ok, result = save_uploaded_image(file, app.config["UPLOAD_FOLDER"])
            if not ok:
                flash(result, "error")
                return render_template("create_slide.html")
            image_filename = result
        else:
            flash("Slayt görseli zorunludur.", "error")
            return render_template("create_slide.html")

        conn = get_db()
        conn.execute(
            "INSERT INTO slides (title, description, image, button_text, button_link, sort_order, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, description, image_filename, button_text, button_link, sort_order, now_str()),
        )
        conn.commit()
        conn.close()
        flash("Slayt başarıyla eklendi.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_slide.html")


@app.route("/admin/slides/<int:slide_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_slide(slide_id):
    conn = get_db()
    slide = conn.execute("SELECT * FROM slides WHERE id = ?", (slide_id,)).fetchone()
    if slide is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        button_text = (request.form.get("button_text") or "").strip()
        button_link = (request.form.get("button_link") or "").strip()
        try:
            sort_order = int(request.form.get("sort_order") or 0)
        except ValueError:
            sort_order = 0

        if not title:
            flash("Başlık zorunludur.", "error")
            conn.close()
            return render_template("edit_slide.html", slide=slide)

        image_filename = slide["image"]
        file = request.files.get("image")
        if file and file.filename:
            ok, result = save_uploaded_image(file, app.config["UPLOAD_FOLDER"])
            if not ok:
                flash(result, "error")
                conn.close()
                return render_template("edit_slide.html", slide=slide)
            delete_uploaded_image(slide["image"], app.config["UPLOAD_FOLDER"])
            image_filename = result

        conn.execute(
            "UPDATE slides SET title=?, description=?, image=?, button_text=?, button_link=?, sort_order=? WHERE id=?",
            (title, description, image_filename, button_text, button_link, sort_order, slide_id),
        )
        conn.commit()
        conn.close()
        flash("Slayt güncellendi.", "success")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("edit_slide.html", slide=slide)


@app.route("/admin/slides/<int:slide_id>/delete", methods=["POST"])
@admin_required
def delete_slide(slide_id):
    conn = get_db()
    slide = conn.execute("SELECT * FROM slides WHERE id = ?", (slide_id,)).fetchone()
    if slide is None:
        conn.close()
        abort(404)
    delete_uploaded_image(slide["image"], app.config["UPLOAD_FOLDER"])
    conn.execute("DELETE FROM slides WHERE id = ?", (slide_id,))
    conn.commit()
    conn.close()
    flash("Slayt silindi.", "success")
    return redirect(url_for("admin_dashboard"))


# ====== ADMIN - ÜRÜN & STOK YÖNETİMİ ======
def _parse_product_form(form):
    """Form verisini doğrular ve temizlenmiş halini döndürür. Hata varsa listede döner."""
    errors = []
    stok_kodu = (form.get("stok_kodu") or "").strip()
    ad = (form.get("ad") or "").strip()

    if not stok_kodu:
        errors.append("Stok kodu zorunludur.")
    if not ad:
        errors.append("Ürün adı zorunludur.")

    def parse_number(field_name, label, allow_negative=False):
        raw = (form.get(field_name) or "0").replace(",", ".").strip()
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"{label} geçerli bir sayı olmalıdır.")
            return 0
        if not allow_negative and value < 0:
            errors.append(f"{label} negatif olamaz.")
        return value

    adet_raw = parse_number("adet", "Adet")
    adet = int(adet_raw)
    gelis_fiyati = parse_number("gelis_fiyati", "Geliş fiyatı")
    satis_fiyati = parse_number("satis_fiyati", "Satış fiyatı")
    kdv_orani = parse_number("kdv_orani", "KDV oranı")

    return {
        "stok_kodu": stok_kodu,
        "ad": ad,
        "adet": adet,
        "gelis_fiyati": gelis_fiyati,
        "satis_fiyati": satis_fiyati,
        "kdv_orani": kdv_orani,
    }, errors


@app.route("/admin/products")
@admin_required
def admin_products():
    search_query = (request.args.get("q") or "").strip()
    conn = get_db()
    if search_query:
        like = f"%{search_query}%"
        products = conn.execute(
            "SELECT * FROM products WHERE stok_kodu LIKE ? OR ad LIKE ? ORDER BY ad ASC",
            (like, like),
        ).fetchall()
    else:
        products = conn.execute("SELECT * FROM products ORDER BY ad ASC").fetchall()

    total_stock_value = conn.execute(
        "SELECT COALESCE(SUM(adet * gelis_fiyati), 0) AS v FROM products"
    ).fetchone()["v"]
    low_stock_count = conn.execute("SELECT COUNT(*) AS c FROM products WHERE adet <= 5").fetchone()["c"]
    conn.close()

    return render_template(
        "admin_products.html",
        products=products,
        search_query=search_query,
        total_stock_value=f"{total_stock_value:.2f}",
        low_stock_count=low_stock_count,
    )


@app.route("/admin/products/create", methods=["GET", "POST"])
@admin_required
def create_product():
    if request.method == "POST":
        data, errors = _parse_product_form(request.form)

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM products WHERE stok_kodu = ?", (data["stok_kodu"],)
        ).fetchone()
        if existing:
            errors.append("Bu stok kodu zaten kullanılıyor.")

        if errors:
            conn.close()
            for e in errors:
                flash(e, "error")
            return render_template("create_product.html", form=data)

        image_filename = ""
        file = request.files.get("image")
        if file and file.filename:
            ok, result = save_uploaded_image(file, app.config["UPLOAD_FOLDER"])
            if not ok:
                conn.close()
                flash(result, "error")
                return render_template("create_product.html", form=data)
            image_filename = result

        conn.execute(
            "INSERT INTO products (stok_kodu, ad, adet, gelis_fiyati, satis_fiyati, kdv_orani, image, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data["stok_kodu"], data["ad"], data["adet"], data["gelis_fiyati"],
             data["satis_fiyati"], data["kdv_orani"], image_filename, now_str(), now_str()),
        )
        conn.commit()
        conn.close()
        flash("Ürün başarıyla eklendi.", "success")
        return redirect(url_for("admin_products"))

    return render_template("create_product.html", form=None)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        data, errors = _parse_product_form(request.form)

        duplicate = conn.execute(
            "SELECT id FROM products WHERE stok_kodu = ? AND id != ?",
            (data["stok_kodu"], product_id),
        ).fetchone()
        if duplicate:
            errors.append("Bu stok kodu başka bir ürün tarafından kullanılıyor.")

        if errors:
            conn.close()
            for e in errors:
                flash(e, "error")
            # Formu kullanıcının girdiği (henüz kaydedilmemiş) verilerle tekrar göster
            merged = dict(product)
            merged.update(data)
            return render_template("edit_product.html", product=merged)

        image_filename = product["image"]
        file = request.files.get("image")
        if file and file.filename:
            ok, result = save_uploaded_image(file, app.config["UPLOAD_FOLDER"])
            if not ok:
                conn.close()
                flash(result, "error")
                return render_template("edit_product.html", product=product)
            delete_uploaded_image(product["image"], app.config["UPLOAD_FOLDER"])
            image_filename = result

        conn.execute(
            "UPDATE products SET stok_kodu=?, ad=?, adet=?, gelis_fiyati=?, satis_fiyati=?, "
            "kdv_orani=?, image=?, updated_at=? WHERE id=?",
            (data["stok_kodu"], data["ad"], data["adet"], data["gelis_fiyati"],
             data["satis_fiyati"], data["kdv_orani"], image_filename, now_str(), product_id),
        )
        conn.commit()
        conn.close()
        flash("Ürün güncellendi.", "success")
        return redirect(url_for("admin_products"))

    conn.close()
    return render_template("edit_product.html", product=product)


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        abort(404)
    delete_uploaded_image(product["image"], app.config["UPLOAD_FOLDER"])
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Ürün silindi.", "success")
    return redirect(url_for("admin_products"))


# ====== ADMIN - MESAJLAR ======
@app.route("/admin/messages/<int:message_id>/read", methods=["POST"])
@admin_required
def mark_message_read(message_id):
    conn = get_db()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    if msg is None:
        conn.close()
        abort(404)
    conn.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/messages/<int:message_id>/delete", methods=["POST"])
@admin_required
def delete_message(message_id):
    conn = get_db()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    if msg is None:
        conn.close()
        abort(404)
    conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    flash("Mesaj silindi.", "success")
    return redirect(url_for("admin_dashboard"))


# ====== HATA SAYFALARI ======
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(e):
    flash("Yüklemeye çalıştığınız dosya çok büyük (maksimum 5 MB).", "error")
    return redirect(request.referrer or url_for("index")), 413


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ====== UYGULAMA BAŞLANGICI ======
def ensure_folders():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "images"), exist_ok=True)


# Klasörler ve veritabanı, uygulama bir WSGI sunucusu (gunicorn vb.) ile
# import edildiğinde de hazır olsun diye modül yüklenirken çalıştırılır
# (sadece __main__ bloğuna bırakılmaz).
ensure_folders()
init_db()


if __name__ == "__main__":
    debug_mode = FLASK_ENV != "production"
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)

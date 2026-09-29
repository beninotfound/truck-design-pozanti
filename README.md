# Truck Design Pozantı

Tır, kamyon ve ticari araç aksesuarları için Flask tabanlı, admin panelli kurumsal web sitesi.

## Teknolojiler

- Python 3 / Flask
- Jinja2 şablonlar
- SQLite (ham `sqlite3` modülü, parametreli sorgular)
- Flask-WTF (CSRF koruması)
- Werkzeug (parola hashleme)
- Pillow (yüklenen görsellerin doğrulanması)
- Vanilla JS / CSS3 (framework yok)

## Kurulum

```bash
# 1) Proje klasörüne girin
cd truck-design-pozanti

# 2) Sanal ortam oluşturun (önerilir)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3) Gerekli paketleri kurun
pip install -r requirements.txt

# 4) .env dosyasını oluşturun
cp .env.example .env
# .env dosyasını açıp SECRET_KEY ve WHATSAPP_NUMBER değerlerini güncelleyin
# Rastgele güçlü bir SECRET_KEY üretmek için:
python -c "import secrets; print(secrets.token_hex(32))"
```

## İlk Admin Hesabını Oluşturma

Uygulamada varsayılan/hazır bir admin hesabı **yoktur** — güvenlik gereği şifre kod
içine yazılmaz. İlk admin hesabınızı aşağıdaki komutla oluşturun:

```bash
python create_admin.py
```

Sizden kullanıcı adı ve şifre istenecek (şifre terminalde görünmez, `getpass` kullanılır).
Şifreniz veritabanına **asla düz metin olarak değil**, `werkzeug.security.generate_password_hash`
ile hashlenerek kaydedilir. Bu script daha sonra da çalıştırılabilir; aynı kullanıcı adını
tekrar girerseniz şifresi güncellenir.

## Çalıştırma

```bash
# Geliştirme modu
export FLASK_ENV=development   # Windows: set FLASK_ENV=development
python app.py
```

Uygulama ilk çalıştığında `database.db` dosyasını ve gerekli tüm tabloları otomatik oluşturur.
Ardından tarayıcıdan:

- Site: http://127.0.0.1:5000/
- Admin girişi: http://127.0.0.1:5000/admin/login

adreslerine gidebilirsiniz.

### Production için

`debug=True` **asla** production'da açık bırakılmamalıdır (uzaktan kod çalıştırma riski).
`FLASK_ENV=production` (veya bu değişkeni hiç tanımlamayın — varsayılan zaten `production`dır)
ile çalıştırdığınızda debug modu otomatik kapalıdır. Gerçek bir sunucuda uygulamayı doğrudan
`python app.py` ile değil, bir WSGI sunucusuyla (örn. `gunicorn app:app`) ve HTTPS arkasında
çalıştırmanız önerilir; bu durumda `SESSION_COOKIE_SECURE` otomatik olarak aktif olur.

## WhatsApp Numarasını Değiştirme

`.env` dosyasındaki `WHATSAPP_NUMBER` değişkenini güncellemeniz yeterlidir (başında `+` olmadan,
ülke kodu ile, örn. `905321234567`). Site genelinde tüm WhatsApp bağlantıları bu değeri kullanır.

## Klasör Yapısı

```
truck-design-pozanti/
├── app.py                 # Flask uygulaması ve tüm route'lar
├── db.py                  # SQLite bağlantısı ve şema
├── security.py             # Güvenli dosya yükleme ve yardımcı fonksiyonlar
├── create_admin.py         # İlk admin hesabını oluşturma script'i
├── requirements.txt
├── .env.example
├── database.db              # (otomatik oluşturulur, git'e eklenmez)
├── templates/
│   ├── base.html, index.html, hizmetler.html, galeri.html,
│   ├── hakkimizda.html, iletisim.html,
│   ├── admin_login.html, admin.html,
│   ├── create_post.html, edit_post.html,
│   ├── create_slide.html, edit_slide.html,
│   └── 404.html, 500.html
└── static/
    ├── css/style.css
    ├── js/script.js
    ├── images/
    └── uploads/            # yüklenen görseller (otomatik oluşturulur)
```

## Admin Paneli Özellikleri

- **Dashboard:** toplam gönderi, toplam slider, toplam mesaj (okunmamış sayısı ile), toplam ve
  bugünkü benzersiz ziyaretçi sayısı.
- **Gönderiler:** ekle / düzenle / sil, fotoğraflı.
- **Slider:** ekle / düzenle / sil — başlık, açıklama, buton yazısı, buton linki, sıra alanları ile.
- **Mesajlar:** iletişim formundan gelen mesajlar, okundu/okunmadı durumu, silme.

## Alınan Güvenlik Önlemleri

| Konu | Önlem |
|---|---|
| SQL Injection | Tüm sorgular `?` parametreleriyle çalışır, hiçbir yerde string birleştirme yok |
| XSS | Jinja2 autoescape açık, hiçbir yerde `\|safe` kullanılmıyor |
| CSRF | Flask-WTF `CSRFProtect` tüm formlarda `csrf_token()` ile aktif |
| Parola güvenliği | `generate_password_hash` / `check_password_hash` (salt'lı hash), düz metin şifre hiçbir yerde yok |
| Dosya yükleme | Uzantı beyaz listesi (jpg/jpeg/png/webp), `uuid4` ile yeniden adlandırma, Pillow ile gerçek görsel doğrulama, 5MB boyut limiti |
| Path traversal | `secure_filename` + `os.path.commonpath` kontrolü, orijinal dosya adı asla kullanılmıyor |
| Session güvenliği | `HttpOnly`, `SameSite=Lax`, production'da `Secure` cookie, 2 saatlik oturum süresi |
| Brute-force | Aynı IP'den 10 dakikada 5'ten fazla başarısız girişte geçici kilitleme |
| Yetkisiz erişim | Tüm `/admin/*` endpoint'leri `admin_required` dekoratörü ile korunur |
| Silme işlemleri | GET yerine CSRF token'lı POST formu ile yapılır |
| Hata yönetimi | Özel 404/500 sayfaları, stack trace kullanıcıya asla gösterilmez (`debug=False`) |

## Notlar

- Google Maps: `templates/iletisim.html` içindeki `<iframe src="...">` alanını kendi konumunuzla değiştirin.
- Instagram/Facebook linkleri `templates/iletisim.html` içinde `#` olarak bırakılmıştır, kendi
  sayfa linklerinizle değiştirin.
- Ziyaretçi sayacı, aynı IP'nin aynı gün içinde tekrar tekrar sayfayı yenileyerek istatistiği
  şişirmesini `visits` tablosundaki `(ip_hash, visit_date)` UNIQUE kısıtı ile engeller.

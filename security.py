"""
security.py
-------------------------------------------------------
Güvenli dosya yükleme ve yardımcı güvenlik fonksiyonları.
-------------------------------------------------------
"""
import os
import uuid
import hashlib
from werkzeug.utils import secure_filename
from PIL import Image

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_MIME_PREFIXES = ("image/",)


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def save_uploaded_image(file_storage, upload_folder: str):
    """
    Yüklenen bir dosyayı güvenli şekilde diske kaydeder.

    Alınan önlemler:
      - Uzantı beyaz listesi (png/jpg/jpeg/webp)
      - Orijinal dosya adı asla kullanılmaz -> uuid4 ile yeniden adlandırma
        (path traversal ve dosya çakışması engellenir)
      - secure_filename() ile ekstra temizleme
      - Pillow ile dosyanın GERÇEKTEN bir görsel olduğu doğrulanır
        (uzantısı .jpg olan çalıştırılabilir/script dosyalarını engeller)
      - Boyut kontrolü app.config['MAX_CONTENT_LENGTH'] ile Flask seviyesinde yapılır

    Başarılıysa (True, kaydedilen_dosya_adi) döner.
    Başarısızsa (False, hata_mesaji) döner.
    """
    if file_storage is None or file_storage.filename == "":
        return False, "Dosya seçilmedi."

    original_name = secure_filename(file_storage.filename)
    if not original_name or not allowed_file(original_name):
        return False, "Sadece JPG, JPEG, PNG ve WEBP dosyalarına izin verilir."

    ext = original_name.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(upload_folder, safe_name)

    # Önce geçici olarak kaydedip Pillow ile doğrula, doğrulama başarısızsa sil.
    file_storage.save(dest_path)

    try:
        with Image.open(dest_path) as img:
            img.verify()  # Gerçek bir görsel mi kontrol eder (bozuk/sahte dosyaları yakalar)
    except Exception:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        return False, "Yüklenen dosya geçerli bir görsel değil."

    return True, safe_name


def delete_uploaded_image(filename: str, upload_folder: str):
    """Verilen dosyayı upload klasöründen güvenli şekilde siler (varsa)."""
    if not filename:
        return
    # secure_filename tekrar uygulanır; klasör dışına çıkışı engeller.
    safe_name = secure_filename(filename)
    path = os.path.join(upload_folder, safe_name)
    if os.path.commonpath([os.path.abspath(path), os.path.abspath(upload_folder)]) != os.path.abspath(upload_folder):
        return  # path traversal denemesi - hiçbir şey yapma
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def hash_ip(ip: str, secret: str) -> str:
    """IP adresini geri döndürülemez şekilde hashler (KVKK/gizlilik + ziyaret sayımı için)."""
    return hashlib.sha256(f"{secret}:{ip}".encode("utf-8")).hexdigest()


def get_client_ip(request) -> str:
    """
    İstemci IP adresini alır. Proxy arkasında çalışıyorsa X-Forwarded-For
    yalnızca güvenilir bir reverse proxy varsa dikkate alınmalıdır; burada
    basitlik için doğrudan remote_addr kullanılır.
    """
    return request.remote_addr or "unknown"

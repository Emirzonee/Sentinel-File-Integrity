import hashlib
import os
import json
import sys
from datetime import datetime

# Ayarlar
BASELINE_FILE = "baseline.json"
CHUNK_SIZE = 4096

def calculate_file_hash(filepath):
    """
   hash hesaplama, ramin sismemesini sağlandi
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(CHUNK_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (FileNotFoundError, PermissionError):
        return None

def load_baseline():
    """
    Daha önce kaydedilmis referans alinacak veritabanini dosyalari yükler  
    """
    if not os.path.exists(BASELINE_FILE):
        return None
    try:
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None

def init_baseline(target_dir="."):
    """
  hashleri kaydeder.
    """
    file_hashes = {}
    print(f"Referans veritabani olusturuluyor: {os.path.abspath(target_dir)}...")
    
    start_time = datetime.now()
    count = 0

    for root, _, files in os.walk(target_dir):
        for file in files:
            filepath = os.path.join(root, file)
            
            # veritabanı dosyasını ve scriptin kendisini tarama dışı bırak
            if file == BASELINE_FILE or file == os.path.basename(__file__):
                continue
            
            file_hash = calculate_file_hash(filepath)
            if file_hash:
                file_hashes[filepath] = file_hash
                count += 1
                # bilgi ver
                sys.stdout.write(f"\rİslenen dosya sayisi: {count}")
                sys.stdout.flush()

    with open(BASELINE_FILE, "w") as f:
        json.dump(file_hashes, f, indent=4)
    
    print(f"\nKurulum tamamlandi. Referans veritabani '{BASELINE_FILE}' a kaydedildi.")
    print(f"Gecen Süre: {datetime.now() - start_time}")

def check_integrity():
    """
    mevcudu referansla kiyasla
    Değisiklik, silinme veya yeni dosya ekleme durumlarini raporlar.
    """
    baseline = load_baseline()
    
    if baseline is None:
        print(f"Hata: Referans dosyasi '{BASELINE_FILE}' bulunamadi veya bozuk.")
        print("Kurulum eksik...Lütfen önce 'python sentinel.py init' komutu ile kurulum yapin.")
        sys.exit(1)

    print("Referans doğrulamasi başlatiliyor...")
    print("-" * 50)
    
    issues_found = 0
    
    # 1. Değişiklik ve Silinme Kontrolü
    for filepath, original_hash in baseline.items():
        if not os.path.exists(filepath):
            print(f"[SİLİNMİS] {filepath}")
            issues_found += 1
            continue
        
        current_hash = calculate_file_hash(filepath)
        if current_hash != original_hash:
            print(f"[DEĞİSTİRİLMİS] {filepath}")
            issues_found += 1

    # 2. Yeni Dosya Kontrolü (Veritabanında olmayan dosyalar)
    for root, _, files in os.walk("."):
        for file in files:
            filepath = os.path.join(root, file)
            # Hariç tutulanlar
            if file == BASELINE_FILE or file == os.path.basename(__file__):
                continue
            
            if filepath not in baseline:
                print(f"[new doc] {filepath}")
                issues_found += 1

    print("-" * 50)
    if issues_found == 0:
        print("Doğrulandi yetkisiz değisiklik tespit edilmedi.")
    else:
        print(f"Uyari: Bütünlük bozuldu! Toplam {issues_found} anomali tespit edildi.")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Sentinel - Dosya Bütünlüğü Doğrulayici (FIM)")
        print("Kullanim:")
        print("  python sentinel.py init   - Referans veritabanini olustur veyahut güncelle")
        print("  python sentinel.py check  - Dosya bütünlüğünü kontrol et")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "init":
        init_baseline()
    elif command == "check":
        check_integrity()
    else:
        print(f"Hata: Bilinmeyen komut '{command}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
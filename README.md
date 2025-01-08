# Auto-Interact
**Tool Auto** `Salam Injeksi Bun` **With AI** 🚀

![1000129967](https://github.com/user-attachments/assets/ee97792f-8639-4ba0-b7a8-d8dbfdf6cf89)

## Yang perlu disiapin
1. **Terminal** (pake *Termux* bisa) 🖥️.
2. **Python** (gw pake versi 3.12.8) 🐍.
3. **Selenium**:
   ```bash
   pip install selenium
   ```
   > Khusus *Termux* pake versi ini:
   ```bash
   pip install selenium==4.9.1
   ```
4. **Chromium** 🌐
   > Termux:
   ```bash
   pkg update
   pkg install tur-repo x11-repo -y
   pkg install chromium
   ```
   > Ubuntu/Debian (APT based)
   ```bash
   sudo apt update
   sudo apt install chromium-browser
   ```
   > Windows

   Gak tau belum nyoba


### Cara Installnya
1. **Clone repo**:
   ```bash
   git clone https://github.com/zevtyardt/auto-interact
   ```
2. **Masuk ke folder**:
   ```bash
   cd auto-interact
   ```
3. **Install dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

## Cara Setting nya
> Step 1: Facebook Session

- **Pertama**: Install extension chrome ini. [Copy Cookies](https://chromewebstore.google.com/detail/copy-cookies/jcbpglbplpblnagieibnemmkiamekcdg) 🍪.
- **Kedua**: Buka [facebook.com](https://facebook.com) terus login pake akun kalian. Sebelum itu, buka pengaturan akun ubah bahasa jadi `Indonesia`.
- **Ketiga**: Buka extension klik Copy Cookies.
- **Keempat**: Simpen cookies tadi didalem folder ni repo, namain jadi `session.json`.

> Step 2: AI Token

- **Pertama**: Caranya sama, bedanya kalian buka web ini [Poe.com](https://poe.com), login pake google aja biar cepet terus copy cookies nya.
- **Kedua**: Paste ke notepad dulu karena token yang dibutuhin cuma `p-b` sama `p-lat` ✏️.
- **Ketiga**: Masuk ke folder ni repo terus buat file `configs.json` isi pake format ini:
  ```json
  [
    {
      "token": {
        "p-b": <Masukin value p-b kesini>,
        "p-lat": <Masukin value p-lat kesini>
      }
    }
  ]
  ```

  Kalian bisa nambahin banyak akun, soalnya 1 akun cuma bisa generate 16 pesan perhari  📩.

## Jalanin Botnya
```bash
python salam-ereksi-bun.py <n>
```
- **n**: Jumlah postingan yang bakal dikomentari, 1-..

Dah gitu aja!

## Donasi 🙏🏻
![1000129454](https://github.com/user-attachments/assets/63c591c1-c2f1-48dd-b39e-786acaf28857)

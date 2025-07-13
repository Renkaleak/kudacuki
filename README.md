# 🤖 Telegram Bot Toko Online

Bot Telegram untuk toko online sederhana dengan fitur:
- Menampilkan produk
- Pemesanan produk
- Metode pembayaran
- Upload bukti pembayaran
- Sistem bantuan

## 🚀 Setup Cepat

### 1. Clone Repository
```bash
git clone <repository-url>
cd telegram-bot-webhook
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Setup Environment Variables
```bash
cp .env.example .env
```

Edit file `.env` dengan informasi Anda:
- `TELEGRAM_TOKEN`: Token bot dari @BotFather
- Informasi pembayaran dan admin

### 4. Buat Bot Telegram
1. Chat dengan @BotFather di Telegram
2. Ketik `/newbot`
3. Ikuti instruksi untuk membuat bot
4. Salin token yang diberikan ke `.env`

## 🌐 Deployment

### Option 1: Vercel (Recommended)
1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
vercel --prod
```

3. Set environment variables di Vercel dashboard

### Option 2: Azure Web Apps
1. Configure Azure Web App name di `.github/workflows/azure-webapps-node.yml`
2. Add secret `AZURE_WEBAPP_PUBLISH_PROFILE` di GitHub
3. Push ke branch `main`

## 📋 Fitur Bot

### Commands:
- `/start` - Mulai bot
- `/products` - Lihat daftar produk
- `/help` - Bantuan
- `/contact` - Kontak admin
- `/order_[ID]` - Pesan produk (contoh: `/order_1`)

### Admin Features:
- Terima bukti pembayaran (foto)
- Notifikasi pesanan baru

## 🔧 Kustomisasi

### Menambah Produk
Edit array `products` di `webhook.js`:
```javascript
const products = [
    {
        id: 1,
        name: 'Nama Produk',
        price: 100000,
        description: 'Deskripsi produk'
    }
];
```

### Mengubah Metode Pembayaran
Edit array `payments` di `webhook.js`:
```javascript
const payments = [
    { type: 'Bank', name: 'BCA', number: '1234567890', holder: 'Nama Pemilik' }
];
```

## 🛡️ Security

- ✅ Token disimpan di environment variables
- ✅ File `.env` di-ignore dari git
- ⚠️ Gunakan HTTPS untuk production
- ⚠️ Validasi input user

## 📞 Support

Jika ada pertanyaan atau masalah, silakan buat issue di repository ini.

## 📝 License

MIT License
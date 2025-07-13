// File: api/webhook.js
// Deploy ke Vercel untuk webhook bot Telegram

const TELEGRAM_TOKEN = '7971269574:AAGMjJw0wSiwWrr-gIecacWJOT2hQhrmteg';

// Products data (gunakan database untuk produksi)
const products = [
    {
        id: 1,
        name: 'Premium Course JavaScript',
        price: 199000,
        description: 'Course lengkap JavaScript dari dasar hingga advanced'
    },
    {
        id: 2,
        name: 'E-book Web Development',
        price: 99000,
        description: 'Panduan lengkap menjadi web developer'
    }
];

// Payment methods
const payments = [
    { type: 'Bank', name: 'BCA', number: '1234567890', holder: 'Nama Pemilik' },
    { type: 'E-wallet', name: 'DANA', number: '081234567890', holder: 'Nama Pemilik' }
];

export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    try {
        const update = req.body;
        const message = update.message;

        if (message) {
            const chatId = message.chat.id;
            const text = message.text;
            const from = message.from;

            console.log('Message from:', from.first_name, text);

            let response = '';

            if (text === '/start') {
                response = `🛍️ <strong>Selamat datang di Toko Online!</strong>

Terima kasih ${from.first_name} telah menggunakan bot kami.

📋 <strong>Menu:</strong>
/products - Lihat produk
/help - Bantuan
/contact - Kontak admin`;

            } else if (text === '/products') {
                response = '🛍️ <strong>Daftar Produk:</strong>\n\n';
                products.forEach((product, index) => {
                    response += `${index + 1}. <strong>${product.name}</strong>\n`;
                    response += `💰 Rp ${product.price.toLocaleString('id-ID')}\n`;
                    response += `📝 ${product.description}\n`;
                    response += `➡️ Pesan: /order_${product.id}\n\n`;
                });

            } else if (text === '/help') {
                response = `❓ <strong>Bantuan</strong>

📋 <strong>Cara Berbelanja:</strong>
1. Ketik /products untuk melihat produk
2. Pilih produk dengan /order_[ID]
3. Lakukan pembayaran sesuai instruksi
4. Kirim bukti pembayaran (foto)
5. Tunggu konfirmasi admin

💬 Admin: @youradmin`;

            } else if (text === '/contact') {
                response = `📞 <strong>Kontak</strong>

💬 Admin: @youradmin
📱 WhatsApp: 081234567890

Jam operasional: 09:00 - 21:00 WIB`;

            } else if (text.startsWith('/order_')) {
                const productId = parseInt(text.split('_')[1]);
                const product = products.find(p => p.id === productId);

                if (product) {
                    response = `📦 <strong>Detail Pesanan</strong>

Produk: ${product.name}
Harga: Rp ${product.price.toLocaleString('id-ID')}

💳 <strong>Metode Pembayaran:</strong>\n`;

                    payments.forEach(payment => {
                        response += `${payment.type === 'Bank' ? '🏦' : '📱'} ${payment.name}: ${payment.number} a.n. ${payment.holder}\n`;
                    });

                    response += `\n📸 Setelah transfer, kirim bukti pembayaran ke sini.
⏰ Batas waktu: 1x24 jam`;
                } else {
                    response = '❌ Produk tidak ditemukan.';
                }

            } else if (message.photo) {
                response = `✅ <strong>Bukti Pembayaran Diterima</strong>

Terima kasih ${from.first_name}!
Bukti pembayaran sedang diverifikasi.

⏰ Konfirmasi dalam 1-24 jam
💬 Jika ada pertanyaan, hubungi admin.`;

            } else {
                response = `Terima kasih atas pesan Anda: "${text}"

Ketik /help untuk melihat menu bantuan.`;
            }

            // Send response
            await fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: chatId,
                    text: response,
                    parse_mode: 'HTML'
                })
            });
        }

        res.status(200).json({ status: 'ok' });
    } catch (error) {
        console.error('Webhook error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
}

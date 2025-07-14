import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import random
import string
import json
import os
from datetime import datetime, timedelta

# Konfigurasi
TOKEN = "7595684644:AAEgjHE4-rGPvqB0WZvZKz10Q1wC05tI1Ik"
ADMIN_CHAT_ID = "7388662787"  # Chat ID admin
PATH_QRIS = "qris.jpg"  # File gambar QRIS
DATA_FILE = "data.json"  # File penyimpanan data

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== FUNGSI BANTUAN ==================
def load_data():
    """Memuat data dari file JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'orders': {},
        'users': {},
        'inventory': {
            'netflix': 100,
            'spotify': 100,
            'youtube': 100
        },
        'prices': {
            'netflix': 50000,
            'spotify': 30000,
            'youtube': 40000
        },
        'settings': {
            'maintenance': False,
            'payment_timeout': 3600
        }
    }

def save_data(data):
    """Menyimpan data ke file JSON"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_accounts_db():
    """Load database akun dari file"""
    accounts_db = {
        'netflix': {'available': [], 'used': []},
        'spotify': {'available': [], 'used': []},
        'youtube': {'available': [], 'used': []}
    }
    
    # Load akun untuk setiap service
    for service in ['netflix', 'spotify', 'youtube']:
        filename = f"{service}_accounts.txt"
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line and ':' in line:
                        accounts_db[service]['available'].append(line)
    
    # Load data akun yang sudah terpakai
    if os.path.exists('used_accounts.json'):
        with open('used_accounts.json', 'r') as f:
            used_data = json.load(f)
            for service in ['netflix', 'spotify', 'youtube']:
                if service in used_data:
                    accounts_db[service]['used'] = used_data[service]
                    # Remove used accounts from available
                    for acc in used_data[service]:
                        if acc in accounts_db[service]['available']:
                            accounts_db[service]['available'].remove(acc)
    
    return accounts_db

def save_used_account(service, account):
    """Simpan akun yang sudah terpakai"""
    used_data = {}
    if os.path.exists('used_accounts.json'):
        with open('used_accounts.json', 'r') as f:
            used_data = json.load(f)
    
    if service not in used_data:
        used_data[service] = []
    
    if account not in used_data[service]:
        used_data[service].append(account)
    
    with open('used_accounts.json', 'w') as f:
        json.dump(used_data, f, indent=2)

def get_available_account(service):
    """Ambil akun yang tersedia dari database"""
    accounts_db = load_accounts_db()
    
    if accounts_db[service]['available']:
        # Ambil akun pertama yang tersedia
        account = accounts_db[service]['available'][0]
        # Tandai sebagai terpakai
        save_used_account(service, account)
        return account
    
    return None

def check_stock_realtime(service):
    """Cek stok akun real-time dari database"""
    accounts_db = load_accounts_db()
    return len(accounts_db[service]['available'])

# ================== HANDLER USER ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk command /start"""
    user = update.effective_user
    data = load_data()
    
    # Cek maintenance mode
    if data['settings'].get('maintenance', False) and str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text(
            "🔧 <b>Bot sedang dalam maintenance.</b>\n"
            "Silakan coba lagi nanti.",
            parse_mode='HTML'
        )
        return
    
    if str(user.id) not in data['users']:
        data['users'][str(user.id)] = {
            'first_name': user.first_name,
            'username': user.username,
            'join_date': datetime.now().isoformat(),
            'orders': []
        }
        save_data(data)
    
    keyboard = [
        [InlineKeyboardButton("🎬 Netflix Premium", callback_data='product_netflix')],
        [InlineKeyboardButton("🎵 Spotify Premium", callback_data='product_spotify')],
        [InlineKeyboardButton("▶️ YouTube Premium", callback_data='product_youtube')],
        [
            InlineKeyboardButton("💳 Cara Pembayaran", callback_data='payment_help'),
            InlineKeyboardButton("📦 Pesanan Saya", callback_data='my_orders')
        ]
    ]
    
    # Tambahkan tombol admin jika user adalah admin
    if str(user.id) == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("👨‍💻 Admin Panel", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Halo {user.first_name}!\n"
        "Selamat datang di bot penjualan akun premium.\n\n"
        "🛍️ <b>Layanan Tersedia:</b>\n"
        "• Netflix Premium 1 Bulan\n"
        "• Spotify Premium 1 Bulan\n"
        "• YouTube Premium 1 Bulan\n\n"
        "💰 <b>Pembayaran:</b> QRIS\n"
        "⚡ <b>Pengiriman:</b> Otomatis setelah pembayaran",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk callback query"""
    query = update.callback_query
    await query.answer()
    data = load_data()
    
    # Handler untuk produk
    if query.data.startswith('product_'):
        service = query.data.replace('product_', '')
        
        if data['inventory'][service] <= 0:
            await query.edit_message_text(
                f"⚠️ Maaf, stok {service.capitalize()} Premium sedang habis.\n"
                "Silakan coba lagi nanti.",
                parse_mode='HTML'
            )
            return

        price = data['prices'][service]
        keyboard = [
            [InlineKeyboardButton("💳 Beli Sekarang", callback_data=f'buy_{service}')],
            [InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(
            f"<b>🔹 {service.capitalize()} Premium</b>\n\n"
            f"💰 <b>Harga:</b> Rp {price:,}\n"
            f"📦 <b>Stok:</b> {data['inventory'][service]}\n"
            f"⏱️ <b>Durasi:</b> 1 Bulan\n\n"
            "✅ <b>Keuntungan:</b>\n"
            "• Akses penuh semua fitur premium\n"
            "• Garansi 7 hari\n"
            "• Pengiriman otomatis\n"
            "• Support 24/7",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif query.data.startswith('buy_'):
        service = query.data.replace('buy_', '')
        
        # Cek stok real-time
        real_stock = check_stock_realtime(service)
        
        if real_stock <= 0:
            await query.edit_message_text(
                f"⚠️ Stok {service.capitalize()} habis!\n"
                "Silakan coba lagi nanti atau pilih produk lain.",
                parse_mode='HTML'
            )
            return

        # Generate order ID
        order_id = 'ORD' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        price = data['prices'][service]
        
        # Simpan order
        data['orders'][order_id] = {
            'order_id': order_id,
            'service': service,
            'user_id': str(query.from_user.id),
            'username': query.from_user.username,
            'price': price,
            'status': 'pending',
            'order_date': datetime.now().isoformat()
        }
        
        if str(query.from_user.id) in data['users']:
            data['users'][str(query.from_user.id)]['orders'].append(order_id)
        
        save_data(data)

        # Kirim QRIS
        try:
            if os.path.exists(PATH_QRIS):
                with open(PATH_QRIS, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.from_user.id,
                        photo=photo,
                        caption=f"<b>🚀 Pembayaran {service.capitalize()} Premium</b>\n\n"
                               f"💰 <b>Total:</b> Rp {price:,}\n"
                               f"📦 <b>Order ID:</b> <code>{order_id}</code>\n\n"
                               "📝 <b>Cara Pembayaran:</b>\n"
                               "1. Scan QRIS di atas\n"
                               "2. Bayar sesuai nominal\n"
                               "3. Kirim screenshot bukti pembayaran\n\n"
                               "⏱️ Pembayaran akan kadaluarsa dalam 1 jam",
                        parse_mode='HTML'
                    )
            else:
                # Jika file QRIS tidak ada, kirim instruksi teks saja
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=f"<b>🚀 Pembayaran {service.capitalize()} Premium</b>\n\n"
                         f"💰 <b>Total:</b> Rp {price:,}\n"
                         f"📦 <b>Order ID:</b> <code>{order_id}</code>\n\n"
                         "📝 Silakan transfer ke:\n"
                         "Bank BCA: 1234567890\n"
                         "a.n. Toko Premium\n\n"
                         "Kirim bukti pembayaran setelah transfer.",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Error sending payment instruction: {e}")
            await query.edit_message_text(
                "⚠️ Terjadi kesalahan. Silakan coba lagi.",
                parse_mode='HTML'
            )
            return

        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu", callback_data='back_to_menu')]]
        await query.edit_message_text(
            f"✅ Order berhasil dibuat!\n\n"
            f"📨 Instruksi pembayaran telah dikirim.\n"
            f"Silakan cek pesan Anda.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif query.data == 'payment_help':
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]]
        await query.edit_message_text(
            "<b>📌 Cara Pembayaran:</b>\n\n"
            "1️⃣ Pilih layanan yang diinginkan\n"
            "2️⃣ Klik tombol 'Beli Sekarang'\n"
            "3️⃣ Scan QRIS yang dikirimkan\n"
            "4️⃣ Bayar sesuai nominal\n"
            "5️⃣ Kirim screenshot bukti pembayaran\n"
            "6️⃣ Tunggu verifikasi admin\n"
            "7️⃣ Akun akan dikirim otomatis\n\n"
            "💡 <b>Tips:</b> Pastikan nominal transfer sesuai!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif query.data == 'my_orders':
        user_id = str(query.from_user.id)
        if user_id not in data['users'] or not data['users'][user_id]['orders']:
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]]
            await query.edit_message_text(
                "📭 Anda belum memiliki pesanan.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            return
        
        user_orders = data['users'][user_id]['orders']
        text = "<b>📦 Riwayat Pesanan Anda:</b>\n\n"
        
        # Tampilkan 5 pesanan terakhir
        for order_id in user_orders[-5:]:
            if order_id in data['orders']:
                order = data['orders'][order_id]
                status_emoji = {
                    'pending': '🟡',
                    'completed': '🟢',
                    'cancelled': '🔴'
                }.get(order['status'], '⚪')
                
                order_date = datetime.fromisoformat(order['order_date']).strftime('%d/%m/%Y %H:%M')
                text += (
                    f"{status_emoji} <b>{order['service'].capitalize()}</b>\n"
                    f"🆔 <code>{order_id}</code>\n"
                    f"💰 Rp {order['price']:,}\n"
                    f"📅 {order_date}\n\n"
                )
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif query.data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("🎬 Netflix Premium", callback_data='product_netflix')],
            [InlineKeyboardButton("🎵 Spotify Premium", callback_data='product_spotify')],
            [InlineKeyboardButton("▶️ YouTube Premium", callback_data='product_youtube')],
            [
                InlineKeyboardButton("💳 Cara Pembayaran", callback_data='payment_help'),
                InlineKeyboardButton("📦 Pesanan Saya", callback_data='my_orders')
            ]
        ]
        
        if str(query.from_user.id) == ADMIN_CHAT_ID:
            keyboard.append([InlineKeyboardButton("👨‍💻 Admin Panel", callback_data='admin_panel')])
        
        await query.edit_message_text(
            "<b>🛍️ Pilih Layanan:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    # Admin handlers
    elif query.data == 'admin_panel':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            await query.answer("❌ Akses ditolak!", show_alert=True)
            return
        await show_admin_panel(query)
    
    elif query.data == 'admin_dashboard':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await show_admin_dashboard(query, data)
    
    elif query.data == 'admin_orders':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await show_pending_orders(query, data)
    
    elif query.data == 'admin_stock':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await show_stock_management(query, data)
    
    elif query.data == 'admin_prices':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await show_price_management(query, data)
    
    elif query.data == 'clear_used_accounts':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        
        # Clear used accounts
        if os.path.exists('used_accounts.json'):
            os.remove('used_accounts.json')
        
        await query.answer("✅ Database akun used telah dihapus!", show_alert=True)
        await show_stock_management(query, data)
    
    elif query.data == 'export_accounts':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        
        accounts_db = load_accounts_db()
        export_text = "📄 <b>Export Akun Premium</b>\n\n"
        
        for service in ['netflix', 'spotify', 'youtube']:
            export_text += f"<b>{service.upper()} - Tersedia ({len(accounts_db[service]['available'])}):</b>\n"
            
            if accounts_db[service]['available']:
                # Tampilkan max 5 akun sebagai preview
                for i, acc in enumerate(accounts_db[service]['available'][:5]):
                    email = acc.split(':')[0]
                    export_text += f"{i+1}. <code>{email}</code>\n"
                
                if len(accounts_db[service]['available']) > 5:
                    export_text += f"... dan {len(accounts_db[service]['available']) - 5} lainnya\n"
            else:
                export_text += "- Kosong\n"
            
            export_text += "\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='admin_stock')]]
        
        await query.edit_message_text(
            export_text + "<i>File lengkap ada di: netflix_accounts.txt, spotify_accounts.txt, youtube_accounts.txt</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    # Update handler untuk broadcast
    elif query.data == 'admin_broadcast':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        context.user_data['admin_action'] = 'broadcast'
        await query.edit_message_text(
            "📢 <b>Broadcast Message</b>\n\n"
            "Kirim pesan yang ingin di-broadcast ke semua user:",
            parse_mode='HTML'
        )
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        
        keyboard = [
            [InlineKeyboardButton("📺 Tambah Netflix", callback_data='add_netflix')],
            [InlineKeyboardButton("🎵 Tambah Spotify", callback_data='add_spotify')],
            [InlineKeyboardButton("▶️ Tambah YouTube", callback_data='add_youtube')],
            [InlineKeyboardButton("📋 Lihat Format", callback_data='show_format')],
            [InlineKeyboardButton("🔙 Kembali", callback_data='admin_dashboard')]
        ]
        
        await query.edit_message_text(
            "➕ <b>Tambah Akun Premium</b>\n\n"
            "Pilih layanan yang ingin ditambah akunnya:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif query.data.startswith('add_'):
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        
        service = query.data.replace('add_', '')
        context.user_data['admin_action'] = 'add_accounts'
        context.user_data['service'] = service
        
        current_stock = check_stock_realtime(service)
        
        await query.edit_message_text(
            f"📝 <b>Tambah Akun {service.capitalize()}</b>\n\n"
            f"Stok saat ini: {current_stock}\n\n"
            f"Kirim akun dalam format:\n"
            f"<code>email:password</code>\n\n"
            f"Contoh:\n"
            f"<code>user@gmail.com:pass123</code>\n\n"
            f"Bisa kirim multiple akun (1 per baris)",
            parse_mode='HTML'
        )
    
    elif query.data == 'show_format':
        await query.edit_message_text(
            "📋 <b>Format Akun Premium</b>\n\n"
            "<b>Format yang benar:</b>\n"
            "<code>email:password</code>\n\n"
            "<b>Contoh untuk Netflix:</b>\n"
            "<code>john@gmail.com:Pass123!\n"
            "sarah@yahoo.com:Secret456\n"
            "mike@hotmail.com:Premium789</code>\n\n"
            "<b>Tips:</b>\n"
            "• 1 akun per baris\n"
            "• Jangan ada spasi\n"
            "• Pastikan akun aktif\n"
            "• Test dulu sebelum add\n\n"
            "File akun tersimpan di:\n"
            "• <code>netflix_accounts.txt</code>\n"
            "• <code>spotify_accounts.txt</code>\n"
            "• <code>youtube_accounts.txt</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Kembali", callback_data='admin_add_accounts')]
            ])
        )
    
    elif query.data == 'admin_stats':
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await show_detailed_stats(query, data)
    
    # Stock management callbacks (removed - using account database now)
    
    # Price management callbacks
    elif query.data.startswith('price_'):
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await handle_price_update(query, context, data)
    
    # Order verification/deletion
    elif query.data.startswith('verify_'):
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await verify_order(query, context, data)
    
    elif query.data.startswith('delete_'):
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await delete_order(query, context, data)
    
    # View order details
    elif query.data.startswith('view_'):
        if str(query.from_user.id) != ADMIN_CHAT_ID:
            return
        await view_order_details(query, data)

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk bukti pembayaran"""
    if not update.message or not update.message.photo:
        return
        
    data = load_data()
    user = update.effective_user
    user_id = str(user.id)
    photo = update.message.photo[-1].file_id
    
    # Cari order pending user
    if user_id not in data['users']:
        await update.message.reply_text(
            "⚠️ Anda belum terdaftar. Silakan /start terlebih dahulu.",
            parse_mode='HTML'
        )
        return
    
    user_orders = data['users'][user_id]['orders']
    pending_orders = [
        o for o in user_orders 
        if o in data['orders'] and data['orders'][o]['status'] == 'pending'
    ]
    
    if not pending_orders:
        await update.message.reply_text(
            "⚠️ Tidak ada pesanan yang menunggu pembayaran.\n"
            "Silakan buat pesanan terlebih dahulu.",
            parse_mode='HTML'
        )
        return
    
    # Ambil order terbaru
    order_id = pending_orders[-1]
    order = data['orders'][order_id]
    
    # Update status order
    order['payment_proof'] = photo
    order['payment_date'] = datetime.now().isoformat()
    save_data(data)
    
    # Kirim notifikasi ke admin
    try:
        keyboard = [
            [
                InlineKeyboardButton("✅ Verifikasi", callback_data=f"verify_{order_id}"),
                InlineKeyboardButton("❌ Tolak", callback_data=f"delete_{order_id}")
            ],
            [InlineKeyboardButton("👁️ Lihat Detail", callback_data=f"view_{order_id}")]
        ]
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 <b>Bukti Pembayaran Baru!</b>\n\n"
                 f"🆔 Order: <code>{order_id}</code>\n"
                 f"👤 User: @{user.username or 'N/A'}\n"
                 f"📦 Produk: {order['service'].capitalize()}\n"
                 f"💰 Nominal: Rp {order['price']:,}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID, 
            photo=photo,
            caption=f"Bukti pembayaran untuk order {order_id}"
        )
        
    except Exception as e:
        logger.error(f"Gagal mengirim notifikasi ke admin: {e}")
    
    await update.message.reply_text(
        "✅ <b>Bukti pembayaran diterima!</b>\n\n"
        "Mohon tunggu, admin akan memverifikasi pembayaran Anda.\n"
        "Estimasi: 5-15 menit",
        parse_mode='HTML'
    )

# ================== ADMIN FUNCTIONS ==================
async def show_admin_panel(query):
    """Tampilkan panel admin"""
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data='admin_dashboard')],
        [InlineKeyboardButton("📦 Pesanan Pending", callback_data='admin_orders')],
        [
            InlineKeyboardButton("📦 Kelola Stok", callback_data='admin_stock'),
            InlineKeyboardButton("💰 Kelola Harga", callback_data='admin_prices')
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast'),
            InlineKeyboardButton("📈 Statistik", callback_data='admin_stats')
        ],
        [InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]
    ]
    
    await query.edit_message_text(
        "👨‍💻 <b>Admin Panel</b>\n\n"
        "Pilih menu yang ingin diakses:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_admin_dashboard(query, data):
    """Dashboard admin dengan statistik"""
    today = datetime.now().date()
    
    # Hitung statistik
    total_orders = len(data['orders'])
    pending_orders = sum(1 for o in data['orders'].values() if o['status'] == 'pending')
    completed_orders = sum(1 for o in data['orders'].values() if o['status'] == 'completed')
    cancelled_orders = sum(1 for o in data['orders'].values() if o['status'] == 'cancelled')
    
    # Pendapatan hari ini
    today_income = 0
    for order in data['orders'].values():
        if order['status'] == 'completed' and 'complete_date' in order:
            complete_date = datetime.fromisoformat(order['complete_date']).date()
            if complete_date == today:
                today_income += order['price']
    
    # Total pendapatan
    total_income = sum(o['price'] for o in data['orders'].values() if o['status'] == 'completed')
    
    # Get real-time stock from database
    netflix_stock = check_stock_realtime('netflix')
    spotify_stock = check_stock_realtime('spotify')
    youtube_stock = check_stock_realtime('youtube')
    
    text = (
        "📊 <b>Dashboard Admin</b>\n\n"
        f"📈 <b>Statistik Order:</b>\n"
        f"• Total: {total_orders}\n"
        f"• Pending: {pending_orders} 🟡\n"
        f"• Selesai: {completed_orders} 🟢\n"
        f"• Dibatalkan: {cancelled_orders} 🔴\n\n"
        f"💰 <b>Pendapatan:</b>\n"
        f"• Hari ini: Rp {today_income:,}\n"
        f"• Total: Rp {total_income:,}\n\n"
        f"📦 <b>Stok Akun (Real-time):</b>\n"
        f"• Netflix: {netflix_stock}\n"
        f"• Spotify: {spotify_stock}\n"
        f"• YouTube: {youtube_stock}\n\n"
        f"👥 <b>Total User:</b> {len(data['users'])}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data='admin_dashboard')],
        [InlineKeyboardButton("➕ Tambah Akun", callback_data='admin_add_accounts')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_pending_orders(query, data):
    """Tampilkan daftar pesanan pending"""
    pending = [(oid, o) for oid, o in data['orders'].items() if o['status'] == 'pending']
    
    if not pending:
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')]]
        await query.edit_message_text(
            "📭 Tidak ada pesanan yang menunggu verifikasi.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return
    
    # Sort by date
    pending.sort(key=lambda x: x[1]['order_date'], reverse=True)
    
    text = "📋 <b>Pesanan Pending:</b>\n\n"
    keyboard = []
    
    for i, (order_id, order) in enumerate(pending[:5]):
        order_date = datetime.fromisoformat(order['order_date']).strftime('%d/%m %H:%M')
        username = order.get('username', 'N/A')
        has_proof = '✅' if 'payment_proof' in order else '❌'
        
        text += (
            f"{i+1}. <code>{order_id}</code> {has_proof}\n"
            f"   📦 {order['service'].capitalize()} | 💰 Rp {order['price']:,}\n"
            f"   👤 @{username} | 📅 {order_date}\n\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(f"✅ {order_id}", callback_data=f"verify_{order_id}"),
            InlineKeyboardButton(f"❌", callback_data=f"delete_{order_id}"),
            InlineKeyboardButton(f"👁️", callback_data=f"view_{order_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')])
    
    await query.edit_message_text(
        text + "✅ = Ada bukti bayar | ❌ = Belum ada bukti",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_stock_management(query, data):
    """Kelola stok dengan tombol inline"""
    text = "📦 <b>Kelola Stok</b>\n\n"
    keyboard = []
    
    for service in ['netflix', 'spotify', 'youtube']:
        stock = data['inventory'][service]
        text += f"<b>{service.capitalize()}:</b> {stock} unit\n"
        
        keyboard.append([
            InlineKeyboardButton(f"{service.capitalize()}", callback_data=f"dummy"),
            InlineKeyboardButton("➖10", callback_data=f"stock_{service}_minus10"),
            InlineKeyboardButton("➖1", callback_data=f"stock_{service}_minus1"),
            InlineKeyboardButton("➕1", callback_data=f"stock_{service}_plus1"),
            InlineKeyboardButton("➕10", callback_data=f"stock_{service}_plus10"),
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data='admin_stock'),
        InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')
    ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_price_management(query, data):
    """Kelola harga dengan tombol inline"""
    text = "💰 <b>Kelola Harga</b>\n\n"
    keyboard = []
    
    for service in ['netflix', 'spotify', 'youtube']:
        price = data['prices'][service]
        text += f"<b>{service.capitalize()}:</b> Rp {price:,}\n"
        
        keyboard.append([
            InlineKeyboardButton(f"{service.capitalize()}", callback_data=f"dummy"),
            InlineKeyboardButton("-10k", callback_data=f"price_{service}_minus10000"),
            InlineKeyboardButton("-5k", callback_data=f"price_{service}_minus5000"),
            InlineKeyboardButton("+5k", callback_data=f"price_{service}_plus5000"),
            InlineKeyboardButton("+10k", callback_data=f"price_{service}_plus10000"),
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data='admin_prices'),
        InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')
    ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_price_update(query, context, data):
    """Update harga produk"""
    parts = query.data.split('_')
    service = parts[1]
    action = parts[2]
    
    if action == 'minus10000':
        data['prices'][service] = max(5000, data['prices'][service] - 10000)
    elif action == 'minus5000':
        data['prices'][service] = max(5000, data['prices'][service] - 5000)
    elif action == 'plus5000':
        data['prices'][service] += 5000
    elif action == 'plus10000':
        data['prices'][service] += 10000
    
    save_data(data)
    await query.answer(f"✅ Harga {service} diupdate!", show_alert=True)
    await show_price_management(query, data)

async def verify_order(query, context, data):
    """Verifikasi dan kirim akun ke user"""
    order_id = query.data.replace('verify_', '')
    
    if order_id not in data['orders']:
        await query.answer("❌ Order tidak ditemukan!", show_alert=True)
        return
    
    order = data['orders'][order_id]
    
    if order['status'] != 'pending':
        await query.answer("❌ Order sudah diproses!", show_alert=True)
        return
    
    # Ambil akun dari database
    account = get_available_account(order['service'])
    
    if not account:
        await query.answer(
            f"❌ Stok {order['service']} habis! Tidak ada akun tersedia.", 
            show_alert=True
        )
        await query.edit_message_text(
            f"❌ Gagal verifikasi {order_id}: Stok habis!\n"
            f"Silakan refund atau tunggu restock.",
            parse_mode='HTML'
        )
        return
    
    # Update order
    order['status'] = 'completed'
    order['account'] = account
    order['complete_date'] = datetime.now().isoformat()
    
    # Note: Tidak perlu kurangi stok manual karena sudah otomatis
    # berkurang saat ambil akun dari database
    
    save_data(data)
    
    # Kirim akun ke user
    try:
        # Parse email:password
        email, password = account.split(':')
        
        message_text = (
            f"🎉 <b>Pembayaran Terverifikasi!</b>\n\n"
            f"📦 <b>Detail Pesanan:</b>\n"
            f"• Order ID: <code>{order_id}</code>\n"
            f"• Produk: {order['service'].capitalize()} Premium\n"
            f"• Durasi: 1 Bulan\n\n"
            f"🔑 <b>Detail Akun:</b>\n"
            f"📧 Email: <code>{email}</code>\n"
            f"🔐 Password: <code>{password}</code>\n\n"
            f"📌 <b>Cara Penggunaan:</b>\n"
            f"1. Login menggunakan email & password di atas\n"
            f"2. JANGAN ubah password\n"
            f"3. JANGAN share ke orang lain\n"
            f"4. Max 1 device bersamaan\n\n"
            f"⚠️ <b>Penting:</b>\n"
            f"• Garansi 7 hari jika ada masalah\n"
            f"• Screenshot ini untuk bukti\n"
            f"• Hubungi admin jika ada kendala"
        )
        
        await context.bot.send_message(
            chat_id=int(order['user_id']),
            text=message_text,
            parse_mode='HTML'
        )
        
        await query.answer("✅ Order berhasil diverifikasi!", show_alert=True)
        await query.edit_message_text(
            f"✅ Order {order_id} telah diverifikasi dan akun telah dikirim ke user.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error sending account: {e}")
        await query.answer("⚠️ Gagal mengirim akun ke user!", show_alert=True)

async def delete_order(query, context, data):
    """Hapus/batalkan order"""
    order_id = query.data.replace('delete_', '')
    
    if order_id not in data['orders']:
        await query.answer("❌ Order tidak ditemukan!", show_alert=True)
        return
    
    order = data['orders'][order_id]
    
    # Update status
    order['status'] = 'cancelled'
    order['cancel_date'] = datetime.now().isoformat()
    save_data(data)
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=int(order['user_id']),
            text=f"❌ <b>Pesanan Dibatalkan</b>\n\n"
                 f"Order ID: <code>{order_id}</code>\n"
                 f"Produk: {order['service'].capitalize()}\n\n"
                 f"Alasan: Pembayaran tidak valid atau expired.\n"
                 f"Silakan buat pesanan baru jika ingin melanjutkan.",
            parse_mode='HTML'
        )
    except:
        pass
    
    await query.answer("✅ Order berhasil dibatalkan!", show_alert=True)
    await query.edit_message_text(
        f"🔴 Order {order_id} telah dibatalkan.",
        parse_mode='HTML'
    )

async def view_order_details(query, data):
    """Lihat detail order"""
    order_id = query.data.replace('view_', '')
    
    if order_id not in data['orders']:
        await query.answer("❌ Order tidak ditemukan!", show_alert=True)
        return
    
    order = data['orders'][order_id]
    user_id = order['user_id']
    user_info = data['users'].get(user_id, {})
    
    status_emoji = {
        'pending': '🟡 Pending',
        'completed': '🟢 Completed',
        'cancelled': '🔴 Cancelled'
    }.get(order['status'], '⚪ Unknown')
    
    text = (
        f"📋 <b>Detail Order</b>\n\n"
        f"🆔 Order ID: <code>{order_id}</code>\n"
        f"📦 Produk: {order['service'].capitalize()}\n"
        f"💰 Harga: Rp {order['price']:,}\n"
        f"📊 Status: {status_emoji}\n\n"
        f"👤 <b>Info User:</b>\n"
        f"• ID: <code>{user_id}</code>\n"
        f"• Username: @{order.get('username', 'N/A')}\n"
        f"• Nama: {user_info.get('first_name', 'N/A')}\n\n"
        f"📅 <b>Tanggal:</b>\n"
        f"• Order: {datetime.fromisoformat(order['order_date']).strftime('%d/%m/%Y %H:%M')}\n"
    )
    
    if 'payment_date' in order:
        text += f"• Bayar: {datetime.fromisoformat(order['payment_date']).strftime('%d/%m/%Y %H:%M')}\n"
    
    if 'complete_date' in order:
        text += f"• Selesai: {datetime.fromisoformat(order['complete_date']).strftime('%d/%m/%Y %H:%M')}\n"
    
    if 'cancel_date' in order:
        text += f"• Batal: {datetime.fromisoformat(order['cancel_date']).strftime('%d/%m/%Y %H:%M')}\n"
    
    if 'account' in order and order['status'] == 'completed':
        text += f"\n🔑 <b>Akun:</b>\n<code>{order['account']}</code>"
    
    keyboard = []
    
    if order['status'] == 'pending':
        keyboard.append([
            InlineKeyboardButton("✅ Verifikasi", callback_data=f"verify_{order_id}"),
            InlineKeyboardButton("❌ Batalkan", callback_data=f"delete_{order_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='admin_orders')])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_detailed_stats(query, data):
    """Tampilkan statistik detail"""
    # Hitung statistik per produk
    stats = {
        'netflix': {'pending': 0, 'completed': 0, 'revenue': 0},
        'spotify': {'pending': 0, 'completed': 0, 'revenue': 0},
        'youtube': {'pending': 0, 'completed': 0, 'revenue': 0}
    }
    
    for order in data['orders'].values():
        service = order['service']
        if order['status'] == 'pending':
            stats[service]['pending'] += 1
        elif order['status'] == 'completed':
            stats[service]['completed'] += 1
            stats[service]['revenue'] += order['price']
    
    text = "📈 <b>Statistik Detail</b>\n\n"
    
    for service in ['netflix', 'spotify', 'youtube']:
        s = stats[service]
        text += (
            f"<b>{service.capitalize()}:</b>\n"
            f"• Pending: {s['pending']}\n"
            f"• Selesai: {s['completed']}\n"
            f"• Pendapatan: Rp {s['revenue']:,}\n\n"
        )
    
    # Top users
    user_orders = {}
    for order in data['orders'].values():
        if order['status'] == 'completed':
            user_id = order['user_id']
            if user_id not in user_orders:
                user_orders[user_id] = 0
            user_orders[user_id] += 1
    
    if user_orders:
        sorted_users = sorted(user_orders.items(), key=lambda x: x[1], reverse=True)[:5]
        text += "<b>🏆 Top Users:</b>\n"
        for i, (user_id, count) in enumerate(sorted_users, 1):
            user = data['users'].get(user_id, {})
            username = user.get('username', 'N/A')
            text += f"{i}. @{username} - {count} order\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle teks dari admin"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if 'admin_action' not in context.user_data:
        return
    
    action = context.user_data['admin_action']
    
    if action == 'broadcast':
        data = load_data()
        message = update.message.text
        
        # Kirim ke semua user
        success = 0
        failed = 0
        
        for user_id in data['users']:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=f"📢 <b>Pengumuman:</b>\n\n{message}",
                    parse_mode='HTML'
                )
                success += 1
            except:
                failed += 1
        
        await update.message.reply_text(
            f"✅ Broadcast selesai!\n"
            f"Berhasil: {success}\n"
            f"Gagal: {failed}"
        )
        
    elif action == 'add_accounts':
        service = context.user_data.get('service')
        if not service:
            await update.message.reply_text("❌ Error: Service tidak ditemukan")
            context.user_data.clear()
            return
        
        # Parse akun dari pesan
        accounts_text = update.message.text
        new_accounts = []
        
        for line in accounts_text.split('\n'):
            line = line.strip()
            if line and ':' in line:
                # Validasi format
                parts = line.split(':')
                if len(parts) == 2:
                    email, password = parts
                    if '@' in email and len(password) > 0:
                        new_accounts.append(line)
        
        if not new_accounts:
            await update.message.reply_text(
                "❌ Tidak ada akun valid!\n"
                "Pastikan format: email:password"
            )
            return
        
        # Simpan ke file
        filename = f"{service}_accounts.txt"
        
        # Append ke file yang sudah ada
        with open(filename, 'a') as f:
            for account in new_accounts:
                f.write(account + '\n')
        
        # Update stok
        new_stock = check_stock_realtime(service)
        
        await update.message.reply_text(
            f"✅ <b>Berhasil menambah akun!</b>\n\n"
            f"Service: {service.capitalize()}\n"
            f"Akun ditambah: {len(new_accounts)}\n"
            f"Total stok sekarang: {new_stock}\n\n"
            f"Detail akun yang ditambah:\n" +
            '\n'.join([f"• <code>{acc.split(':')[0]}</code>" for acc in new_accounts]),
            parse_mode='HTML'
        )
        
        # Kembali ke dashboard
        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data='admin_dashboard')],
            [InlineKeyboardButton("➕ Tambah Lagi", callback_data='admin_add_accounts')]
        ]
        
        await update.message.reply_text(
            "Pilih menu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Clear state
    context.user_data.clear()

# ================== ADMIN COMMANDS ==================
async def add_netflix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command untuk tambah akun Netflix"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Format salah!\n\n"
            "Gunakan: /addnetflix email:password\n"
            "Contoh: /addnetflix user@gmail.com:pass123"
        )
        return
    
    account = ' '.join(context.args)
    if ':' not in account:
        await update.message.reply_text("❌ Format harus email:password")
        return
    
    # Simpan ke file
    with open('netflix_accounts.txt', 'a') as f:
        f.write(account + '\n')
    
    new_stock = check_stock_realtime('netflix')
    await update.message.reply_text(
        f"✅ Akun Netflix berhasil ditambah!\n"
        f"Stok sekarang: {new_stock}"
    )

async def add_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command untuk tambah akun Spotify"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Format salah!\n\n"
            "Gunakan: /addspotify email:password"
        )
        return
    
    account = ' '.join(context.args)
    if ':' not in account:
        await update.message.reply_text("❌ Format harus email:password")
        return
    
    with open('spotify_accounts.txt', 'a') as f:
        f.write(account + '\n')
    
    new_stock = check_stock_realtime('spotify')
    await update.message.reply_text(
        f"✅ Akun Spotify berhasil ditambah!\n"
        f"Stok sekarang: {new_stock}"
    )

async def add_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command untuk tambah akun YouTube"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Format salah!\n\n"
            "Gunakan: /addyoutube email:password"
        )
        return
    
    account = ' '.join(context.args)
    if ':' not in account:
        await update.message.reply_text("❌ Format harus email:password")
        return
    
    with open('youtube_accounts.txt', 'a') as f:
        f.write(account + '\n')
    
    new_stock = check_stock_realtime('youtube')
    await update.message.reply_text(
        f"✅ Akun YouTube berhasil ditambah!\n"
        f"Stok sekarang: {new_stock}"
    )

async def check_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command untuk cek stok semua produk"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    accounts_db = load_accounts_db()
    
    text = "📦 <b>Stok Akun Premium</b>\n\n"
    
    for service in ['netflix', 'spotify', 'youtube']:
        available = len(accounts_db[service]['available'])
        used = len(accounts_db[service]['used'])
        
        text += (
            f"<b>{service.capitalize()}:</b>\n"
            f"• Tersedia: {available}\n"
            f"• Terpakai: {used}\n"
            f"• Total: {available + used}\n\n"
        )
    
    await update.message.reply_text(text, parse_mode='HTML')
def main():
    """Jalankan bot"""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", lambda u, c: show_admin_panel(u.callback_query) if u.callback_query else None))
    
    # Admin command handlers
    application.add_handler(CommandHandler("addnetflix", add_netflix))
    application.add_handler(CommandHandler("addspotify", add_spotify))
    application.add_handler(CommandHandler("addyoutube", add_youtube))
    application.add_handler(CommandHandler("stock", check_stock_command))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(handle_button))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_payment))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))
    
    # Start bot
    logger.info("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Initialize data file if not exists
    if not os.path.exists(DATA_FILE):
        initial_data = {
            'orders': {},
            'users': {},
            'inventory': {
                'netflix': 100,
                'spotify': 100,
                'youtube': 100
            },
            'prices': {
                'netflix': 50000,
                'spotify': 30000,
                'youtube': 40000
            },
            'settings': {
                'maintenance': False,
                'payment_timeout': 3600
            }
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    # Create account files if not exist
    for service in ['netflix', 'spotify', 'youtube']:
        filename = f"{service}_accounts.txt"
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                # Create empty file
                pass
            logger.info(f"Created {filename}")
    
    # Create used accounts file if not exist
    if not os.path.exists('used_accounts.json'):
        with open('used_accounts.json', 'w') as f:
            json.dump({}, f)
    
    logger.info("Bot initialization complete")
    main()

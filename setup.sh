#!/bin/bash

echo "🤖 Setup Telegram Bot Toko Online"
echo "=================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js tidak terinstall. Silakan install Node.js terlebih dahulu."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm tidak terinstall. Silakan install npm terlebih dahulu."
    exit 1
fi

echo "✅ Node.js dan npm terdeteksi"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Membuat file .env..."
    cp .env.example .env
    echo "✅ File .env dibuat. Silakan edit file .env dengan informasi Anda."
else
    echo "ℹ️  File .env sudah ada."
fi

echo ""
echo "🎉 Setup selesai!"
echo ""
echo "📋 Langkah selanjutnya:"
echo "1. Edit file .env dengan token bot Telegram Anda"
echo "2. Untuk development lokal: npm run dev"
echo "3. Untuk deploy ke Vercel: vercel --prod"
echo ""
echo "📖 Baca README.md untuk panduan lengkap"
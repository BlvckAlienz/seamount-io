#!/bin/bash
# File: frontend/fix-build.sh
# ✅ AGGRESSIVE CACHE CLEAR & BUILD FIX

echo "🧹 Starting aggressive cache clear..."

# 1. Kill all Node/Vite processes
echo "1️⃣ Killing all dev servers..."
pkill -f "vite" || true
pkill -f "node" || true
sleep 2

# 2. Remove ALL cache directories
echo "2️⃣ Removing cache directories..."
rm -rf node_modules/.vite
rm -rf node_modules/.cache
rm -rf .vite
rm -rf dist
rm -rf .turbo

# 3. Clear npm cache
echo "3️⃣ Clearing npm cache..."
npm cache clean --force

# 4. Reinstall dependencies (fresh)
echo "4️⃣ Reinstalling dependencies..."
rm -rf node_modules
rm -f package-lock.json
npm install

# 5. Rebuild from scratch
echo "5️⃣ Building from scratch..."
npm run build

# 6. Start dev server
echo "6️⃣ Starting dev server..."
echo "✅ Cache cleared! Starting Vite dev server..."
echo "🌐 Open browser and hard refresh (Ctrl+Shift+R / Cmd+Shift+R)"
npm run dev
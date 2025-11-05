#!/bin/bash

# Add .tsx extension to all @/components imports
find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i -E \
  "s|from '@/components/([^'\"]+)'|from '@/components/\1.tsx'|g" {} +

# Fix double extensions if any exist
find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i \
  "s|\.tsx\.tsx|.tsx|g" {} +

echo "✅ Extensions added"
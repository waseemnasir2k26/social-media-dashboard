@echo off
echo Starting Social Media Dashboard Frontend...
cd frontend
if not exist node_modules (
    echo Installing dependencies...
    npm install
)
npm run dev

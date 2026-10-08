@echo off
cd /d %~dp0
where pnpm >nul 2>&1 && (pnpm install & pnpm dev) || (npm install & npm run dev)

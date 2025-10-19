# Sensei's Updater

A safe, colorized Windows maintenance helper:

- **Drivers** via Windows Update (Drivers category), with robust PSWindowsUpdate handling  
- **App updates** via `winget` with dynamic selection and profile saving  
- Create **Restore Point**, clean **TEMP & Recycle Bin**, **DISM/SFC** health scan, view **startup** apps  
- Works in **user or admin** context; asks for admin only when needed  
- UTF-8 + ANSI console output to avoid encoding issues

> **Tip**  
> Run **as Administrator** for Drivers / Cleanup / DISM+SFC.  
> Run **without admin** for Microsoft Store app updates.

> **Enjoying the updater?**  
> Buy me a coffee: **https://ko-fi.com/senseiissei**

## Quick start

```powershell
# From repo root
py -3 -m pip install --upgrade pip
py -3 -m pip install -e .
python -m sensei_updater
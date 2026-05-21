"""
AuraSafe — setup.py
One-command setup: installs deps, optionally builds .exe
Usage:
  python setup.py          → install deps only
  python setup.py --exe    → install deps + build .exe
"""

import subprocess, sys, os, platform

REQUIRED     = ["flask", "flask-cors", "psutil"]
WINDOWS_EXTRAS = ["pywin32"]
EXE_DEPS     = ["pyinstaller"]

def run(cmd):
    print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗  {result.stderr.strip()[:120]}")
        return False
    print("  ✓  Done")
    return True

def main():
    build_exe = "--exe" in sys.argv

    print("╔══════════════════════════════════╗")
    print("║    AuraSafe Setup v2.5           ║")
    print("╚══════════════════════════════════╝")
    print(f"Python  : {sys.version.split()[0]}")
    print(f"Platform: {platform.system()}\n")

    print("Installing core dependencies...")
    for pkg in REQUIRED:
        run([sys.executable, "-m", "pip", "install", pkg, "-q", "--break-system-packages"])

    if platform.system() == "Windows":
        print("\nInstalling Windows extras...")
        for pkg in WINDOWS_EXTRAS:
            run([sys.executable, "-m", "pip", "install", pkg, "-q", "--break-system-packages"])

    if build_exe:
        print("\nInstalling PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q", "--break-system-packages"])
        print("\nBuilding .exe (this may take a few minutes)...")
        os.chdir(os.path.join(os.path.dirname(__file__), "backend"))
        run([sys.executable, "-m", "PyInstaller", "aurasafe.spec", "--clean", "--noconfirm"])
        print("\n✅ AuraSafe.exe created in backend/dist/")

    print("\n✅ Setup complete!\n")
    print("▶  To run:")
    print("   cd backend && python main.py")
    print("\n🌐 Dashboard opens at: http://127.0.0.1:5000")
    print("\n🔌 Chrome Extension:")
    print("   1. chrome://extensions → Enable Dev Mode")
    print("   2. Load unpacked → select 'extension' folder")

    if platform.system() == "Windows":
        print("\n⚡ Auto-startup:")
        print("   Run startup/install_startup_windows.bat as Administrator")

if __name__ == "__main__":
    main()

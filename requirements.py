import os
import struct
import subprocess
import sys
import urllib.request
import zipfile


def download_file(url, dest_path):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    print(f"Downloading: {url}")
    urllib.request.urlretrieve(url, dest_path)


def ensure_embedded_python():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    py_dir = os.path.join(base_dir, ".python311")
    python_exe = os.path.join(py_dir, "python.exe")
    if os.path.exists(python_exe):
        return python_exe

    is_64bit = struct.calcsize("P") * 8 == 64
    if not is_64bit:
        print("Ошибка: требуется 64-bit Python для MediaPipe.")
        sys.exit(1)

    zip_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    zip_path = os.path.join(py_dir, "python-3.11.9-embed-amd64.zip")
    download_file(zip_url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(py_dir)

    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = os.path.join(py_dir, "get-pip.py")
    download_file(get_pip_url, get_pip_path)

    subprocess.check_call([python_exe, get_pip_path])
    enable_site_packages(py_dir)
    return python_exe


def enable_site_packages(py_dir):
    pth_files = [f for f in os.listdir(py_dir) if f.endswith("._pth")]
    if not pth_files:
        return
    pth_path = os.path.join(py_dir, pth_files[0])
    with open(pth_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    if "Lib\\site-packages" not in lines:
        lines.append("Lib\\site-packages")
    if "import site" not in lines:
        lines.append("import site")

    with open(pth_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    python_exe = sys.executable
    if sys.version_info >= (3, 13):
        print(
            "Текущий Python 3.13+ не поддерживается MediaPipe.\n"
            "Скачаю portable Python 3.11 локально в проект (без переустановки)."
        )
        python_exe = ensure_embedded_python()
        enable_site_packages(os.path.dirname(python_exe))

    if python_exe.lower().endswith("pythonw.exe"):
        python_exe = os.path.join(os.path.dirname(python_exe), "python.exe")

    subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed successfully.")
    print(f"Run the app with:\n  \"{python_exe}\" main.py")

    try:
        choice = input("Start the app now? (y/n): ").strip().lower()
    except EOFError:
        choice = "n"
    if choice == "y":
        subprocess.check_call([python_exe, os.path.join(os.path.dirname(__file__), "main.py")])


if __name__ == "__main__":
    main()

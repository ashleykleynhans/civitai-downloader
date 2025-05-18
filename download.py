#!/usr/bin/env python3
import sys
import argparse
import requests
from pathlib import Path
from urllib.parse import unquote
from time import time
import platform

TOKEN_FILE = Path.home() / '.civitai' / 'config'
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible)',
}


def get_token():
    try:
        return TOKEN_FILE.read_text().strip()
    except FileNotFoundError:
        token = input("Enter your CivitAI API token: ").strip()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token)
        return token


def extract_filename(resp):
    cd = resp.headers.get("Content-Disposition")
    if cd and "filename=" in cd:
        return unquote(cd.split("filename=")[1].strip('"'))
    return Path(resp.url).name  # fallback


def set_file_permissions(filepath):
    if platform.system() != "Windows":
        filepath.chmod(0o644)  # rw-r--r--
        print(f"Permissions set: 644 on {filepath}")
    else:
        print("Skipping permission change on Windows.")


def download_model(url, output_dir, token):
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"

    with requests.get(url, headers=headers, stream=True, allow_redirects=True) as r:
        if r.status_code != 200:
            raise Exception(f"Failed to download. Status: {r.status_code}, URL: {r.url}")

        filename = extract_filename(r)
        output_path = Path(output_dir) / filename
        total = int(r.headers.get('Content-Length', 0))
        downloaded = 0
        start = time()

        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = (downloaded / total) * 100
                        sys.stdout.write(f'\r{filename}: {percent:.2f}%')
                        sys.stdout.flush()

    set_file_permissions(output_path)
    print(f"\n✅ Saved: {output_path.name} ({downloaded // 1024 // 1024} MB in {int(time()-start)}s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="CivitAI model download URL")
    parser.add_argument("output_dir", help="Directory to save the model")
    args = parser.parse_args()

    token = get_token()
    download_model(args.url, args.output_dir, token)


if __name__ == "__main__":
    main()

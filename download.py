#!/usr/bin/env python3
import os
import sys
import argparse
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

CHUNK_SIZE = 1638400
TOKEN_FILE = Path.home() / '.civitai' / 'config'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'


def parse_args():
    parser = argparse.ArgumentParser(description='Batch CivitAI Downloader')
    parser.add_argument('--input', nargs='+', required=True, help='List of model URLs or a path to a text file')
    parser.add_argument('--output', required=True, help='Output directory to store models')
    return parser.parse_args()


def get_token():
    try:
        with open(TOKEN_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        token = input('Enter your CivitAI API token: ').strip()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        return token


def extract_filename_from_redirect(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    content_disp = query_params.get('response-content-disposition', [None])[0]
    if content_disp and 'filename=' in content_disp:
        return unquote(content_disp.split('filename=')[1].strip('"'))
    return None


def download_file(url, output_dir, token):
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': USER_AGENT}

    class NoRedirect(urllib.request.HTTPErrorProcessor):
        def http_response(self, request, response): return response
        https_response = http_response

    req = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    response = opener.open(req)

    if response.status in [301, 302, 303, 307, 308]:
        redirect_url = response.getheader('Location')
        filename = extract_filename_from_redirect(redirect_url)
        if not filename:
            raise Exception("Unable to extract filename from redirect URL")
        response = urllib.request.urlopen(redirect_url)
    else:
        raise Exception(f"Unexpected HTTP status: {response.status}")

    total_size = int(response.getheader('Content-Length', 0))
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'wb') as f:
        downloaded = 0
        start = time.time()
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                percent = (downloaded / total_size) * 100
                sys.stdout.write(f'\r{filename}: {percent:.2f}%')
                sys.stdout.flush()
        sys.stdout.write('\n')
    print(f'Download complete: {filename}')


def main():
    args = parse_args()
    token = get_token()
    urls = []

    for item in args.input:
        if os.path.isfile(item):
            with open(item, 'r') as f:
                urls.extend([line.strip() for line in f if line.strip()])
        else:
            urls.append(item.strip())

    for url in urls:
        try:
            download_file(url, args.output, token)
        except Exception as e:
            print(f'Failed to download {url}: {e}')


if __name__ == '__main__':
    main()

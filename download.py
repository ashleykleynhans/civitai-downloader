#!/usr/bin/env python3
import os
import re
import sys
import argparse
import time
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote


CHUNK_SIZE = 1638400
TOKEN_FILE = Path.home() / '.civitai' / 'config'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
DEFAULT_ENV_NAME = os.getenv('CIVITAI_TOKEN_NAME', 'CIVITAI_TOKEN')
CIVITAI_BASE_URL = os.getenv('CIVITAI_BASE_URL', 'https://civitai.com/api/download/models')


def get_args():
    parser = argparse.ArgumentParser(
        description='CivitAI Downloader',
    )

    parser.add_argument(
        'model_url_or_id',
        type=str,
        help='CivitAI Download Model ID, eg: 46846'
    )

    parser.add_argument(
        'output_path',
        type=str,
        help='Output path, eg: /workspace/stable-diffusion-webui/models/Stable-diffusion'
    )

    return parser.parse_args()


def get_token() -> str | None:
    token = os.getenv(DEFAULT_ENV_NAME, None)
    if token:
        return token
    try:
        with open(TOKEN_FILE, 'r') as file:
            token = file.read().strip()
            return token
    except Exception as e:
        return None


def store_token(token: str) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(TOKEN_FILE, 'w') as file:
        file.write(token)


def prompt_for_civitai_token() -> str:
    token = input('Please enter your CivitAI API token: ')
    store_token(token)
    return token


def extract_id(url: str) -> str | None:
    """
    Extracts the model version ID from a CivitAI URL.
    
    - https://civitai.com/models/1234567?modelVersionId=46846
    """
    # Pattern: query param modelVersionId=XXXX
    match = re.search(r"modelVersionId=(\d+)", url)
    if match:
        return match.group(1)
    return None


def download_file(model_url_or_id: str, output_path: str, token: str) -> None:
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': USER_AGENT,
    }

    # Disable automatic redirect handling
    class NoRedirection(urllib.request.HTTPErrorProcessor):
        def http_response(self, request, response):
            return response
        https_response = http_response

    if model_url_or_id.isdigit():
        url = f'{CIVITAI_BASE_URL}/{model_url_or_id}'
    elif CIVITAI_BASE_URL in model_url_or_id:
        url = model_url_or_id
    elif 'modelVersionId' in model_url_or_id:
        model_id = extract_id(model_url_or_id)
        if model_id:
            url = f'{CIVITAI_BASE_URL}/{model_id}'
    
    if not url:
        raise Exception('Invalid model URL or ID')
        
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(NoRedirection)
    response = opener.open(request)

    if response.status in [301, 302, 303, 307, 308]:
        redirect_url = response.getheader('Location')

        # Handle relative redirects
        if redirect_url.startswith('/'):
            base_url = urlparse(url)
            redirect_url = f"{base_url.scheme}://{base_url.netloc}{redirect_url}"

        # Extract filename from the redirect URL
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        content_disposition = query_params.get('response-content-disposition', [None])[0]

        if content_disposition and 'filename=' in content_disposition:
            filename = unquote(content_disposition.split('filename=')[1].strip('"'))
        else:
            # Fallback: extract filename from URL path
            path = parsed_url.path
            if path and '/' in path:
                filename = path.split('/')[-1]
            else:
                filename = 'downloaded_file'

            if not filename:
                raise Exception('Unable to determine filename')

        response = urllib.request.urlopen(redirect_url)
    elif response.status == 404:
        raise Exception('File not found')
    else:
        raise Exception('No redirect found, something went wrong')

    total_size = response.getheader('Content-Length')

    if total_size is not None:
        total_size = int(total_size)

    output_file = os.path.join(output_path, filename)

    with open(output_file, 'wb') as f:
        downloaded = 0
        start_time = time.time()

        while True:
            chunk_start_time = time.time()
            buffer = response.read(CHUNK_SIZE)
            chunk_end_time = time.time()

            if not buffer:
                break

            downloaded += len(buffer)
            f.write(buffer)
            chunk_time = chunk_end_time - chunk_start_time

            if chunk_time > 0:
                speed = len(buffer) / chunk_time / (1024 ** 2)  # Speed in MB/s

            if total_size is not None:
                progress = downloaded / total_size
                sys.stdout.write(f'\rDownloading: {filename} [{progress*100:.2f}%] - {speed:.2f} MB/s')
                sys.stdout.flush()

    end_time = time.time()
    time_taken = end_time - start_time
    hours, remainder = divmod(time_taken, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        time_str = f'{int(hours)}h {int(minutes)}m {int(seconds)}s'
    elif minutes > 0:
        time_str = f'{int(minutes)}m {int(seconds)}s'
    else:
        time_str = f'{int(seconds)}s'

    sys.stdout.write('\n')
    print(f'Download completed. File saved as: {filename}')
    print(f'Downloaded in {time_str}')

    if output_file.endswith('.zip'):
        print('Note: The downloaded file is a ZIP archive.')
        try:
            with zipfile.ZipFile(output_file, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(output_file))
        except Exception as e:
            print(f'ERROR: Failed to unzip the file. {e}')


def main():
    args = get_args()
    token = get_token()

    if not token:
        token = prompt_for_civitai_token()

    try:
        download_file(args.model_url_or_id, args.output_path, token)
    except Exception as e:
        print(f'ERROR: {e}')


if __name__ == '__main__':
    main()

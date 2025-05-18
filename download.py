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
    parser.add_argument('--url', "-u", nargs='+', required=True, help='List of model URLs or a path to a text file')
    parser.add_argument('--token', "-t", help='CivitAI API token')
    parser.add_argument("--air", "-a", nargs="+", help="Use Artificial Intelligence Resource from CivitAI model page; see https://github.com/civitai/civitai/wiki/AIR-%E2%80%90-Uniform-Resource-Names-for-AI for more")
    parser.add_argument('--local-dir', "-l", required=True, help='Output directory to store models')
    return parser.parse_args()


def get_token():
    try:
        with open(TOKEN_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        token = input('Enter your CivitAI API token: ').strip()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        return token
    except Exception as e:
        print(f'Failed to read token file: {e}')
        sys.exit(1)


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
    if args.air and args.url:
        print('Only one of --url and --air can be specified')
        sys.exit(1)
    token = get_token()
    urls = []
    if args.air is not None:
        """    
        urn: Uniform Resource Name optional
        air: Artificial Intelligence Resource optional
        {ecosystem}: Type of the ecosystem (sd1, sd2, sdxl)
        {type}: Type of the resource (model, lora, embedding, hypernet)
        {source}: Supported network source
        {id}: Id of the resource from the source
        {format}: The format of the model (safetensor, ckpt, diffuser, tensor rt) optional
        """
        for air in args.air:
            # example: urn:air:flux1:lora:civitai:667004@746484
            # https://civitai.com/api/download/models/746484?type=Model&format=SafeTensor
            #
            # parse the air to get the model
            parsed_air = air.split(':')
            if len(parsed_air) < 6:
                print(f'Invalid AIR: {air}')
                continue
            else:
                model_id = parsed_air[5].split('@')
                model_id = model_id[1] if len(model_id) == 2 else model_id[0]
                model_format = parsed_air[6] if len(parsed_air) == 7 else 'safetensor'
                url = f'https://civitai.com/api/download/models/{model_id}?type=Model&format={model_format}'
                urls.append(url)
    if args.url is not None:
        urls = args.url
        for url in urls:
            if not url.startswith('http') or "civitai.com" not in url:
                print(f'Invalid URL: {url}')
                urls.remove(url)
                continue
            else:
                print(f'Found URL: {url}')
    for url in urls:
        try:
            download_file(url, args.output, token)
        except Exception as e:
            print(f'Failed to download {url}: {e}')


if __name__ == '__main__':
    main()

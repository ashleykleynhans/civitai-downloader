#!/usr/bin/env python3
import sys
import argparse
import requests
from pathlib import Path
from time import time
import platform
from urllib.parse import urlparse, parse_qs, unquote
import re

from requests import HTTPError

TOKEN_FILE = Path.home() / '.civitai' / 'config'
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible)',
}
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'


def parse_args():
    parser = argparse.ArgumentParser(description='Batch CivitAI Downloader')

    # Mutually exclusive group: only one of --url or --air
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', '-u', nargs='+',
                       help='List of model URLs or a path to a text file')
    group.add_argument('--air', '-a', nargs='+',
                       help='AIR strings (see https://github.com/civitai/civitai/wiki/AIR-%E2%80%90-Uniform-Resource-Names-for-AI)')

    # Other unrelated flags are declared separately and unaffected by the group
    parser.add_argument("--force-unsafe", action="store_true",
                        help="Allow downloading non-safetensor files (e.g. .ckpt, .pt). Use with caution.")
    parser.add_argument('--token', '-t',
                        help='CivitAI API token (or use ~/.civitai/config)')
    parser.add_argument('--local-dir', '-l', required=True,
                        help='Output directory to store models')
    parser.add_argument('--debug', action='store_true',
                        help='Print debug messages')

    return parser.parse_args()


def parse_air(air_string):
    """
    Parses a CivitAI AIR string into its components:
    urn:air:{ecosystem}:{type}:{source}:{id}@{version}.{format}
    """
    pattern = re.compile(
        r'^(?:urn:)?(?:air:)?'                   # optional prefixes
        r'(?P<ecosystem>[^:]+):'                # ecosystem
        r'(?P<type>[^:]+):'                     # type
        r'(?P<source>[^:]+):'                   # source
        r'(?P<id>[^@\.]+)'                      # resource ID (stops at @ or .)
        r'(?:@(?P<version>[^\.]+))?'            # optional @version
        r'(?:\.(?P<format>\w+))?'               # optional .format
        r'$'
    )

    match = pattern.match(air_string)
    if not match:
        raise ValueError(f"Invalid AIR format: {air_string}")

    return match.groupdict()


def build_civitai_download_url(air: dict) -> str:
    """
    Given parsed AIR components, construct a Civitai model download URL.
    Requires at minimum: source=civitai, and id or version.
    """
    if air.get("source") != "civitai":
        raise ValueError(f"Unsupported source for download: {air.get('source')}")

    # Prefer version ID if present
    resource_id = air.get("version") or air.get("id")
    if not resource_id:
        raise ValueError("No resource ID or version found in AIR.")

    # Type defaults to 'Model' in API query
    type_param = air.get("type", "Model")  # Civitai expects this capitalization
    format_param = air.get("format", "SafeTensor")  # Optional format

    return f"https://civitai.com/api/download/models/{resource_id}?type={type_param}&format={format_param}"


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


def get_model_data(version_id, token=None):
    headers = {
        'User-Agent': USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    print(f"Resolving model format for {version_id}...")
    url = f"https://civitai.com/api/v1/model-versions/{version_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    files = data.get("files", [])
    file = files[0] if files else {}
    return {
        "format": file.get("metadata", {}).get("format", "Other"),
        "type": file.get("type", "Other"),
    }


def download_model(url, local_dir, token):
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"

    with requests.get(url, headers=headers, stream=True, allow_redirects=True) as r:
        if r.status_code in [400, 401, 403]:
            raise requests.HTTPError(f'Access denied for {url}: {r.status_code}')
        elif r.status_code in [404, 410]:
            raise requests.HTTPError(f'Resource not found for {url}: {r.status_code}')
        elif r.status_code in [500, 502, 503, 504]:
            raise requests.HTTPError(f'Server error for {url}: {r.status_code}')

        if "text/html" in r.headers.get("Content-Type", ""):
            raise Exception("Received HTML instead of a file. Possibly an invalid token or expired link.")

        # Optional: force max 3 redirects to avoid infinite loops
        if r.history:
            print(f"Redirected {len(r.history)} times:")
            for resp in r.history:
                print(f" - {resp.status_code} -> {resp.url}")

        filename = extract_filename(r)
        output_path = Path(local_dir) / filename
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
    args = parse_args()
    if args.air and args.url:
        print('Only one of --url and --air can be specified')
        sys.exit(1)
    elif not (args.air or args.url):
        print('At least one of --url or --air must be specified')
    token = get_token()

    validated_urls = []
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
            air_dict = parse_air(air)
            if air_dict.get("format") is None:
                model_data = get_model_data(air_dict.get("version") or air_dict.get("id"), token)
                air_dict["format"] = model_data["format"]
                air_dict["type"] = model_data["type"]
                print(
                    f"Found AIR: {air} (format: {model_data})"
                )
            if not args.force_unsafe and air_dict.get("format", "").lower() != "safetensor":
                print(f"❌ Refusing unsafe format in AIR: {air} (found: {air_dict.get('format')})")
                continue
            url = build_civitai_download_url(air_dict)
            validated_urls.append(url)
    elif args.url is not None:
        for url in args.url:
            if not url.startswith('http') or "civitai.com" not in url:
                print(f'Invalid URL: {url}')
            else:
                print(f'Found URL: {url}')
                validated_urls.append(url)
    for url in validated_urls:
        try:
            download_model(url, args.local_dir, token)
        except Exception as e:
            print(f'Failed to download {url}: {e}')

if __name__ == "__main__":
    main()

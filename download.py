#!/usr/bin/env python3
import argparse
import pathlib
import platform
import re
import sys
from time import time
from urllib.parse import parse_qs, unquote, urlparse

import requests
from requests import HTTPError

TOKEN_FILE = pathlib.Path.home() / ".civitai" / "config"
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible)",
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"


def main():
    args = parse_args()
    token = get_token()
    # We'll map urls to the model data to examine format and files later
    debug = args.debug
    validated_urls = {}
    model_data = {}
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
                model_data = get_model_data(air_dict.get("version"), token, debug=debug)
            url = build_civitai_download_url(air_dict, debug=debug)
            print(
                f"Found AIR: {air} -> {url} (version: {air_dict.get('version')}, format: {model_data.get('format')})"
            )
            validated_urls[url] = model_data
    elif args.url is not None:
        for url in args.url:
            if not url.startswith("http") or "civitai.com" not in url:
                print(f"Invalid URL: {url}")
            else:
                print(f"Found URL: {url}")
                validated_urls[url] = get_model_data(
                    parse_url(url)["version"], token, debug=debug
                )
    for url, md in validated_urls.items():
        print(f"Downloading {url}...")
        try:

            files = select_model_files(files=md["files"], size=args.size, fp=args.fp)
            if files is None:
                print(f"Skipping {url}: No model files match constraints")
                continue
            for f in files:
                print(f"Found file: {f.get('name')}")
                if not args.include_companions and f.get("type", "") != "Model":
                    print(f"Skipping companion file {f.get('name')}")
                elif (
                    not args.force_unsafe
                    and f.get("type", "") == "Model"
                    and f.get("metadata", {}).get("format").lower() != "safetensor"
                ):
                    print(
                        f"Skipping unsafe file {f.get('name')} (type: {f.get('type')})"
                    )
                elif args.size and f.get("metadata", {}).get("size") != args.size:
                    continue
                elif args.fp and str(f.get("metadata", {}).get("fp")) != str(args.fp):
                    continue
                else:
                    print(f"Downloading {f.get('name')}...")
            download_model(url, args.local_dir, token)
        except Exception as e:
            print(f"Failed to download {url}: {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch CivitAI Downloader", add_help=True
    )

    # Mutually exclusive group: only one of --url or --air
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--url", "-u", nargs="+", help="List of model URLs or a path to a text file"
    )
    group.add_argument(
        "--air",
        "-a",
        nargs="+",
        help="AIR strings (see https://github.com/civitai/civitai/wiki/AIR-%%E2%%80%%90-Uniform-Resource-Names-for-AI)",
    )
    parser.add_argument(
        "--size",
        choices=["full", "pruned"],
        help="Only download models with the given size metadata.",
    )
    parser.add_argument(
        "--fp",
        choices=[8, 16, 32],
        help="Only download models with the given floating point precision.",
    )
    # include companion files (e.g. VAE)
    parser.add_argument(
        "--include-companions",
        action="store_true",
        help="Include companion files such as VAE or config YAML",
    )
    # Other unrelated flags are declared separately and unaffected by the group
    parser.add_argument(
        "--force-unsafe",
        action="store_true",
        help="Allow downloading non-safetensor files (e.g. .ckpt, .pt). Use with caution.",
    )
    parser.add_argument(
        "--token", "-t", help="CivitAI API token (or use ~/.civitai/config)"
    )
    parser.add_argument(
        "--local-dir", "-l", required=True, help="Output directory to store models"
    )
    parser.add_argument("--debug", action="store_true", help="Print debug messages")

    return parser.parse_args()


def get_token():
    try:
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        token = input("Enter your CivitAI API token: ").strip()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        return token
    except Exception as e:
        print(f"Failed to read token file: {e}")
        sys.exit(1)


def parse_air(air_string):
    """
    Parses a CivitAI AIR string into its components:
    urn:air:{ecosystem}:{type}:{source}:{id}@{version}.{format}
    """
    pattern = re.compile(
        r"^(?:urn:)?(?:air:)?"  # optional prefixes
        r"(?P<ecosystem>[^:]+):"  # ecosystem
        r"(?P<type>[^:]+):"  # type
        r"(?P<source>[^:]+):"  # source
        r"(?P<id>[^@\.]+)"  # resource ID (stops at @ or .)
        r"(?:@(?P<version>[^\.]+))?"  # optional @version
        r"(?:\.(?P<format>\w+))?"  # optional .format
        r"$"
    )

    match = pattern.match(air_string)
    if not match:
        raise ValueError(f"Invalid AIR format: {air_string}")

    return match.groupdict()


def parse_url(url):
    """
    Parse a Civitai download URL to extract model version ID and query parameters.
    Returns a dict with 'version', 'format', 'size', 'fp', 'type'.
    Raises ValueError if the URL is invalid.
    """
    parsed = urlparse(url)

    # 1. Validate base URL
    if not parsed.scheme.startswith("http") or "civitai.com" not in parsed.netloc:
        raise ValueError(f"Invalid domain in URL: {url}")

    if not parsed.path.startswith("/api/download/models/"):
        raise ValueError(f"Invalid download path in URL: {url}")

    # 2. Extract model version ID
    try:
        version_id = parsed.path.split("/api/download/models/")[1].split("/")[0]
    except IndexError:
        raise ValueError(f"Could not extract model version ID from URL: {url}")

    if not version_id.isdigit():
        raise ValueError(f"Model version ID is not numeric: {version_id}")

    # 3. Extract optional query parameters
    query = parse_qs(parsed.query)

    return {
        "version": version_id,
        "type": extract_options(query, "type"),
        "format": extract_options(query, "format"),
        "size": extract_options(query, "size"),
        "fp": extract_options(query, "fp"),
        "raw_url": url,
    }


def extract_options(q, key):
    return q.get(key, [None])[0]


def get_model_data(version_id, token=None, debug: bool = False):
    headers = {
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    print(f"Resolving model format for {version_id}...")
    url = f"https://civitai.com/api/v1/model-versions/{version_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if debug:
        print(f"Model data: {data}")
    return data


def build_civitai_download_url(air: dict, debug: bool = False) -> str:
    """
    Given parsed AIR components, construct a Civitai model download URL.
    Requires at minimum: source=civitai, and id or version.
    """
    if debug:
        print(f"Constructing download URL for {air}")
    if air.get("source") != "civitai":
        raise ValueError(f"Unsupported source for download: {air.get('source')}")

    # Prefer version ID if present
    resource_id = air.get("version") or air.get("id")
    if not resource_id:
        raise ValueError("No resource ID or version found in AIR.")

    # Type defaults to 'Model' in API query
    type_param = air.get("type", "Model")  # Civitai expects this capitalization
    format_param = air.get("format", "SafeTensor")  # Optional format

    url = f"https://civitai.com/api/download/models/{resource_id}"
    return url


def download_model(url, local_dir, token):
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"

    with requests.get(url, headers=headers, stream=True, allow_redirects=True) as r:
        if r.status_code in [400, 401, 403]:
            raise requests.HTTPError(f"Access denied for {url}: {r.status_code}")
        elif r.status_code in [404, 410]:
            raise requests.HTTPError(f"Resource not found for {url}: {r.status_code}")
        elif r.status_code in [500, 502, 503, 504]:
            raise requests.HTTPError(f"Server error for {url}: {r.status_code}")

        if "text/html" in r.headers.get("Content-Type", ""):
            raise Exception(
                "Received HTML instead of a file. Possibly an invalid token or expired link."
            )

        # Optional: force max 3 redirects to avoid infinite loops
        if r.history:
            print(f"Redirected {len(r.history)} times:")
            for resp in r.history:
                print(f" - {resp.status_code} -> {resp.url}")

        filename = extract_filename(r)
        sanitized_filename = sanitize_filename(filename)
        raw_output_path = pathlib.Path(local_dir) / sanitized_filename
        output_path = raw_output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        start = time()

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = (downloaded / total) * 100
                        sys.stdout.write(f"\r{filename}: {percent:.2f}%")
                        sys.stdout.flush()

    set_file_permissions(output_path)
    print(
        f"\n✅ Saved: {output_path.name} ({downloaded // 1024 // 1024} MB in {int(time()-start)}s)"
    )


def extract_filename(resp):
    cd = resp.headers.get("Content-Disposition")
    if cd and "filename=" in cd:
        return unquote(cd.split("filename=")[1].strip('"'))
    return pathlib.Path(resp.url).name  # fallback


def sanitize_filename(header_filename, default_name=None):
    if not header_filename:
        return default_name
    # Extract the base name to prevent path traversal
    name = pathlib.Path(header_filename).name
    # Remove or replace invalid characters (basic example)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # Ensure it's not empty after sanitization
    if not name.strip():
        print("Warning: Sanitization failed, using default filename.")
        # Fallback to default_name if sanitization fails
        # If no default name is provided, warn and use civitai_download_<timestamp>
        if default_name:
            name = default_name
        else:
            print("Warning: No default filename provided, using civitai_download_<timestamp>.")
            name = f"civitai_download_{int(time())}"
    return name


def set_file_permissions(filepath):
    if platform.system() != "Windows":
        filepath.chmod(0o644)  # rw-r--r--
        print(f"Permissions set: 644 on {filepath}")
    else:
        print("Skipping permission change on Windows.")


def select_model_files(files, size=None, fp=None, include_companions=False):
    model_candidates = [f for f in files if f.get("type") == "Model"]
    companion_candidates = [g for g in files if (g.get("type") in ["VAE", "Other"])]
    filtered = [f for f in model_candidates if matches_constraints(f, size, fp)]
    filtered.extend(companion_candidates)
    return filtered

def matches_constraints(file, size=None, fp=None):
    meta = file.get("metadata", {})
    if size and meta.get("size") != size:
        return False
    if fp and str(meta.get("fp")) != str(fp):
        return False
    return True


if __name__ == "__main__":
    main()

# Bash script to download models from CivitAI using curl

## Installation

```bash
git clone https://github.com/ashleykleynhans/civitai-downloader.git
mv civitai-downloader/download.sh /usr/local/bin/download-model
chmod +x /usr/local/bin/download-model
```
## Usage

```bash
download-model [URL]
```

eg:

```bash
download-model https://civitai.com/api/download/models/15236 
```

## NOTE

1. This assumes you are using RunPod and logged in as `root`
   user.  If not, the installation commands should be prefixed
   with `sudo`.
2. It is important to ensure that you use the **DOWNLOAD** link
and not the link to the model page in CivitAI.

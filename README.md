# CivitAI Stable Diffusion models downloader

**Give this bash script a CivitAI.com model link and it will download the model and places it in the corect folder in your Stable Diffusion (SD) Automatic111 installation. Uses Curl.**

It downloads and installs:
- Checkpoints
- Lora
- LoCon
- Textual Inversions
- Aesthetic Gradients
- Hyper Networks
- VAE

## Installation

### On local mahines:
```bash
git clone https://github.com/ashleykleynhans/civitai-downloader.git
mv civitai-downloader/download.sh /usr/local/bin/download-model
chmod +x /usr/local/bin/download-model
```

### On docker, RunPod.io, etc. 

```shell
git clone https://github.com/ashleykleynhans/civitai-downloader.git
chmod +x /path/to/script/download-model
```

## Configuration

Edit the first variable in the script `path_a1` to point to the Automatic111 directory
```bash
path_a1="/workspace/sd/stable-diffusion-webui/"
```
That's it...

## Usage

```bash
download-model [UI] [type] [link]
```

You specify which SD user interface you are using [UI], what type of SD model you are downloading [type] and lastly the download link of the model from CivitAI.ai [link]. 

Example: 
```bash
download-model a1 lr https://civitai.com/api/download/models/14856
```

[UI]

The Stable Diffusion user interface. Currently only Automatic111 is supported.

| Argument   | User Interface      |
|------------|---------------------|
| a1         | Automatic1111       |

[model type]

| Argument   | SD Model            |
|------------|---------------------|
| cp         | Checkpoint          |
| lr         | Lora                |
| lc         | LoCon               |
| ti         | Textual Inversion   |
| ag         | Aesthetic Gradients |
| hp         | Hyper Network       |
| va         | VAE                 |

[link]

The the model download link NOT the URL of the page.


## NOTE

1. This assumes you are using RunPod and logged in as `root` user.  If not, the installation commands should be prefixed with `sudo`.
2. It is important to ensure that you use the **DOWNLOAD** link and not the link to the model page in CivitAI.

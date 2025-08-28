# Python script to download models from CivitAI using an API key

## Getting Started

This script requires a [CivitAI](https://civitai.com/user/account)
API key.  You can create the API key as follows:

1. Log into [CivitAI](https://civitai.com).
2. Go to the [Manage Account](https://civitai.com/user/account) page.
3. Scroll down to the `API Keys` section, close to the bottom of the page.
4. Click the `+ Add API key` button to create a new API key.
5. Give the API key a name and click the `Save` button.
6. You will then use your newly created API key with this script.

## Installation

```bash
curl -L https://raw.githubusercontent.com/ashleykleynhans/civitai-downloader/main/download.py -o /usr/local/bin/download-model
chmod +x /usr/local/bin/download-model
```

> [!NOTE]
> This assumes you are using RunPod and logged in as `root`
> user.  If not, the installation commands should be prefixed
> with `sudo`.

> [!IMPORTANT]
> It is important to ensure that you use the **DOWNLOAD** link
> and not the link to the model page in CivitAI.
> You can get the model id even from CivitAI main url. Eg. `https://civitai.com/models/1234567?modelVersionId=46846` the model_id will be `46846`

## Usage

```bash
download-model [MODEL_ID] [DESTINATION]
```

To download to the current directory:

```bash
download-model 46846 .
```

To download to a different directory:

```bash
download-model 46846 /workspace/stable-diffusion-webui/models/Stable-diffusion
```

## Community and Contributing

Pull requests and issues on [GitHub](https://github.com/ashleykleynhans/civitai-downloader)
are welcome. Bug fixes and new features are encouraged.

## Appreciate my work?

<a href="https://www.buymeacoffee.com/ashleyk" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>


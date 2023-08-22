#!/usr/bin/env bash

# Configuration: 
# Set the path for your Stable Diffusion UI:

path_a1="/workspace/sd/stable-diffusion-webui/"
#path_comfyui="/Workspace/ComfyUI"

# Nothing to configure below this line, but lots to improve ...

###############################################################################

## Enable dumping some variables
debug=false

# Automatic1111 paths
# Reference: https://github.com/civitai/civitai/wiki/How-to-use-models

a1_checkpoint="${path_a1}models/Stable-diffusion/"
a1_lora="${path_a1}models/Lora/"
a1_locon="${path_a1}models/Lora/"
a1_textual_inversion="${path_a1}embeddings/"
a1_aesthetic_gradients="${path_a1}aesthetic_embeddings/"
a1_hyper_network="${path_a1}models/hypernetworks/"
a1_va="${path_a1}models/VAE/"
# TODO investage wildecards


# ComfyUI Paths
# TODO add ComfyUI support

#------------------------------------------------------------------------------

user_agent_strig="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Accepted UI arguments
array_ui=("a1")

# Accepted model types
array_models=("cp","lr","lc","ti","ag","hn","va")

download_path=false
download_result=""

#------------------------------------------------------------------------------

## Debug
if "$debug" ; then 
  echo 
  echo  "#1: ${1}"
  echo  "#2: ${2}"
  echo  "#3: ${3}"
  echo 
  echo $a1_checkpoint
  echo $a1_lora
  echo $a1_locon
  echo $a1_textual_inversion
  echo $a1_aesthetic_gradients
  echo $a1_hyper_network
  echo $a1_va
  echo 
fi

#------------------------------------------------------------------------------

##
## Validating arguments
##

##  Check for no arguments or help flag, print help text 
if [ "$1" == "-h" ] || [ "$#" = 0 ]; then
cat <<'EOF'

This is a script to simplify the download of Stable Diffusion models from
CivitAI.com and installs them in the correct paths of the Stable Diffuion user
interface of your choice. 

    Usage: $0  <UI>  <Model type>  <Download link>

Argument #1: Specify the Stable Diffuion UI used. Currently only Automatic1111
             is supported so "a1" is the only option.

Argument #2: Define the model type (Checkpoint, Lora, etc.) in order for the
             script to place it in the correct path. Supported models are
             listed below.
    
Argument #3: The download link of the model from the model page, not thr URL of
             the page.

| Argument   | User interface      |
|------------|---------------------|
| a1         | Automatic1111       | 

| Argument   | SD Model            |
|------------|---------------------|
| cp         | Checkpoint          |
| lr         | Lora                |
| lc         | LoCon               |
| ti         | Textual Inversion   |
| ag         | Aesthetic Gradients |
| hp         | Hyper Network       |
| va        | VAE                 |

Configuration: The only configuration needed is to define the SD UI path.
If this is not already configured for you then edit this script and set the
apropriate path for the UI of your choice.

GIT: TODO

EOF
  exit 1
fi

## Checks for the correct number of arguments and exists if incorrect.
if [ "$#" -ne 3 ]; then
cat <<'EOF'
Three arguments needed. Type '$0 -h' for info.

  Usage: $0  <UI>  <Model type>  <Download link>
  
EOF
  exit 1
fi

## Load arguments in variables
ui="${1}"
type="${2}"
link="${3}"

## Checking UI argument
if ! [[ "${array_ui[*]}" =~ "$ui" ]]; then 
  printf "Error: Argument #1 not correct. Should be the UI abreviation, type \'$0 -h\' for more info.\n"
  exit 1  
fi

## Checking models argument
if ! [[ "${array_models[*]}" =~ "$type" ]]; then 
  printf "Error: Argument #2 not correct. Should be the model type abreviation, type \'$0 -h\' for more info.\n"
  exit 1
fi

## Check the provided link for the correct domain
if ! [[ "$link" =~ "https://civitai.com/" ]]; then
  printf "Only models from CivitAI.com are supported. Type \'$0 -h\' for info.\n"
  exit 1
fi

## Checking the provided link that it's for the download link not the page URL
if ! [[ "$link" =~ "https://civitai.com/api" ]]; then
  echo "Incorrect download link provided. You must provide the Download link from CivitAI page, not the link to the model page itself."
  exit 1
fi


## Debug
if "$debug" ; then 
  printf "UI: $ui\n"
  printf "Model: $type\n"
  printf "Link: $link\n"
fi

#------------------------------------------------------------------------------

##
## Main
##

if [ $ui="a1" ] ; then
  case $type in
    cp)
      download_path=$a1_checkpoint
      ;;

    lr)
      download_path=$a1_lora
      ;;
    lc)
      download_path=$a1_locon
      ;;
    ti)
      download_path=$a1_textual_inversion
      ;;
    ag)
      download_path=$a1_aesthetic_gradients
      ;;
    hn)
      download_path=$a1_hyper_network
      ;;
    va)
      download_path=$a1_va
      ;;
   esac    
fi    

# debug
if $debug ; then
  echo 
  echo $download_path    
fi
    
    
## Check download direcotory exist and we have write permission
if ! [ -w $download_path ] ; then
  echo "$download_path does not exist or you do not have right permission"
fi



## Finally, download time
echo "Using curl to download the model file:"
echo "----------------------------------------"
curl -JL --remote-name --user-agent "${user_agent_strig}" "${link}" --output-dir "$download_path"
cmd_status="$?"
echo "----------------------------------------"

if [ $cmd_status == 0 ]; then
  echo "Model file succussfully downloaded in '$download_path' "
else 
  
cat <<'EOF'

Download failed. Check for the error in the curl output above. The curl error 
might help diagnose the issue.

Tip: Does the file already exist? This script does not overwrite exsisting files due
to the large size of some of the models, and cannot currently resume interrupted
downloads.
  
  ERROR: Download Failed.

EOF
  
fi

exit $cmd_status




    
    
    
    




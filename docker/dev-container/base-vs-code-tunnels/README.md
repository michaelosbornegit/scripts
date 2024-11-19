# dev-container/base

This is my base image with all my goodies installed. If I'm just doing basic python/node application stuff, this is what I use

# to expose a gpu for llm stuff

This is a little specific to my unraid server setup

- add the extra runtime parameter `--runtime nvidia`

Set the following container vars

- `NVIDIA_DRIVER_CAPABILITIES` = all
- `NVIDIA_VISIBLE_DEVICES` = the id of the gpu to use, get this from unraid nvidia driver
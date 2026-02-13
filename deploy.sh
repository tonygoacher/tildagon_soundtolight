#!/bin/bash


mpremote mkdir :/apps
mpremote mkdir :/apps/tgstl

mpremote fs cp app.py :/apps/tgstl/
mpremote fs cp metadata.json :/apps/tgstl/
mpremote fs cp tildagon.toml :/apps/tgstl/
mpremote fs cp logo.jpg :/apps/tgstl/
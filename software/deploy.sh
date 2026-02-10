#!/bin/bash


mpremote mkdir :/apps
mpremote mkdir :/apps/first

mpremote fs cp app.py :/apps/first/
mpremote fs cp metadata.json :/apps/first/
mpremote fs cp tildagon.toml :/apps/first/
mpremote fs cp logo.jpg :/apps/first/
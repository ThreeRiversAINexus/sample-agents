#!/bin/sh

docker run -it -v ./:/app -p8080:8080 discussion_show:dev python main.py
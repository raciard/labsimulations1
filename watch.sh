#!/bin/bash
while inotifywait -e modify $1; do pdflatex -interaction=nonstopmode $1; done

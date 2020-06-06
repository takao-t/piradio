#!/bin/sh

convert $1 -strip $1
convert $1 -define png:color-type=6 $1


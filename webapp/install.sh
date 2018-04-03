#!/bin/sh
cp ./build/index.html ../server/templates/index.html
rm -r ../server/static/*
cp -r ./build/static ../server/

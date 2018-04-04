#!/bin/sh
echo "Deploying view.html"
cp ./build/index.html ../../templates/view.html
rm -r ../../static/*
cp -r ./build/static ../../
echo "View only copied!"

#!/bin/sh
echo "Deploying control site"
cp ./build/index.html ../../templates/control.html
rm -r ../../static/*
cp -r ./build/static ../../
echo "Control site deployed!"

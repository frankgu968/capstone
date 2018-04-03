#!/bin/sh
echo "Deploying new site"
cp ./build/index.html ../templates/index.html
rm -r ../capstone/static/*
cp -r ./build/static ../
echo "New site copied!"

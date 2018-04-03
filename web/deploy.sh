#!/bin/sh
echo "Deploying control site"
rm -f ../templates/*
cp ./webapp/build/index.html ../templates/control.html
cp ./viewapp/build/index.html ../templates/view.html
rm -r ../static/*
cp -r ./webapp/build/static ../
cp -r ./viewapp/build/static ../
echo "Control site deployed!"

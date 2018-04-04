#!/bin/sh
cd ./webapp
npm run build &
cd ../viewapp
npm run build &

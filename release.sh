#!/bin/sh

DIST=unstable
if [ ! -z "$1" ]; then
	DIST=$1
fi

if [ -z "$2" ]; then
	dch -i -D $DIST
else
	VER=$2
	dch -v $VER -D $DIST
fi

VER=$(dpkg-parsechangelog | sed -n 's/^Version: //p')
sed -i "s/version.*$/version\": \"$VER\",/" bundle.json

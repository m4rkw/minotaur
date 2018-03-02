#!/bin/bash
if [ "$1" == "" ] ; then
  echo "$0 <tag>"
  exit 0
fi
mkdir minotaur-$1
cp minotaur.exe minotaur-$1/minotaur
cp README.md minotaur-$1/
cp LICENSE minotaur-$1/
cp BENCHMARKS.txt minotaur-$1/
cp minotaur.conf.example minotaur-$1/
tar -zcf minotaur-$1.tar.gz minotaur-$1

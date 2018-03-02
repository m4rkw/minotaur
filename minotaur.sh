#!/bin/bash
BASE=`dirname $0`
cd $BASE
while :
do
  ./minotaur.py --mine
  echo "minotaur crashed :S waiting 2 seconds and restarting..."
  sleep 2
done

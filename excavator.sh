#!/bin/bash
/opt/excavator/bin/excavator -p $1 -d 0 2>&1 1>>/tmp/debug&

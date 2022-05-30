#!/usr/bin/env python3
import argparse
import sys
import re

cli = argparse.ArgumentParser()
cli.add_argument('input')
cli.add_argument('output')
cli.add_argument('scale', type=float)
args = cli.parse_args()

def scalexy(val):
    x = float(val.group(1)) * args.scale
    y = float(val.group(2)) * args.scale
    return '(xy {} {})'.format(x, y)

with open(args.input, 'r') as in_file, open(args.output, 'w', newline='') as out_file:
    for line in in_file:
        line = re.sub(r'\(xy ([0-9-.]+) ([0-9-.]+)\)', scalexy, line)
        out_file.write(line)

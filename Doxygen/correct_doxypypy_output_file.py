# -*- coding: utf-8 -*-
"""
Created on Fri Aug 30 11:04:41 2019

@author: jirka
"""
import sys


def modify_file(filename):

    # Open input file read-only
    with open(filename, 'r') as in_file:
        # Copy input file to temporary file, modifying as we go
        lines = in_file.readlines()

    # Remove all even lines which are empty due to some doxypypy error
    correct_lines = lines[::2]

    # Reopen input file writable
    with open(filename, "w") as out_file:
        # Overwriting original file with temporary file contents
        for line in correct_lines:
            out_file.write(line)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        modify_file(sys.argv[1])
    else:
        print("It's necessary to specify an doxypypy output file")

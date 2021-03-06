#!/usr/bin/env python
"""\
Usage: %prog [options] infile

Groups rows of a tabular data file by the values of a given column.
"""


from swissknife.error import AppError
from swissknife.utils import (
    main_func,
    open_anything,
    parse_index_specification,
    sublist,
)

from collections import defaultdict
from itertools import chain
import optparse
import sys


def create_option_parser():
    """Creates an `OptionParser` that parses the command line
    options."""

    def indexspec_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, parse_index_specification(value))

    parser = optparse.OptionParser(usage=sys.modules[__name__].__doc__.strip())
    parser.add_option(
        "-d",
        "--delimiter",
        metavar="DELIM",
        dest="in_delimiter",
        default="\t",
        help="use DELIM for field delimiter in the input file " "instead of TAB",
    )
    parser.add_option(
        "-D",
        "--output-delimiter",
        metavar="DELIM",
        dest="out_delimiter",
        default=None,
        help="use DELIM for field delimiter in the output file "
        "instead of the input delimiter",
    )
    parser.add_option(
        "-f",
        "--fields",
        metavar="LIST",
        dest="fields",
        default=None,
        action="callback",
        type="str",
        callback=indexspec_callback,
        help="use only these columns from the input. The first "
        "column is always the column to join on.",
    )
    parser.add_option(
        "-u",
        "--unique",
        action="store_true",
        dest="unique",
        default=False,
        help="keep unique entries only",
    )
    parser.add_option(
        "--strip",
        action="store_true",
        dest="strip",
        default=False,
        help="strip leading and trailing whitespace from each line",
    )

    return parser


def process_file(infile, options):
    """Processes the given file."""
    # Calculate the column indices we are interested in
    if options.fields:
        col_idxs = [f - 1 for f in options.fields]
    else:
        col_idxs = None

    # Dictionary to map keys to values
    if options.unique:
        keys_to_values = defaultdict(set)
    else:
        keys_to_values = defaultdict(list)

    # Some caching to avoid costly lookups
    delim = options.in_delimiter
    fields = options.fields
    join = options.out_delimiter.join

    # Set up characters to strip from lines
    chars_to_strip = " \t\r\n" if options.strip else "\r\n"

    for line in open_anything(infile):
        # Split the input line
        parts = line.strip(chars_to_strip).split(delim)

        # Select the relevant columns only
        if col_idxs:
            parts = sublist(parts, col_idxs)

        # If the row is empty, continue
        if not parts:
            continue

        # Store the row to its appropriate key
        if options.unique:
            keys_to_values[parts[0]].update(parts[1:])
        else:
            keys_to_values[parts[0]].extend(parts[1:])

    # Print the key-value pairs
    for key, values in keys_to_values.items():
        print(join(chain([key], values)))


@main_func
def main():
    """Main entry point of the script."""
    parser = create_option_parser()
    options, args = parser.parse_args()

    if options.out_delimiter is None:
        options.out_delimiter = options.in_delimiter

    if options.fields:
        options.fields = list(options.fields)

    if not args:
        args = ["-"]

    for arg in args:
        process_file(arg, options)


if __name__ == "__main__":
    main()

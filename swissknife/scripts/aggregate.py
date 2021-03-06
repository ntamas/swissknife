#!/usr/bin/env python
"""\
Usage: %prog [options] function infile1 infile2 ...

Aggregates data from multiple data files in tabular format and calculates
means/sums/variances.

More precisely, the script needs N input files that are in exactly the same
tabular format, and prints an aggregated file where the jth element in row i
contains the mean/sum/variance/etc of all the N elements in row i/column j
in the N input files.
"""


from swissknife.error import AppError
from swissknife.utils import (
    first,
    flatten,
    last,
    lenient_float,
    main_func,
    mean,
    mean_95ci,
    mean_err,
    mean_sd,
    median,
    only_numbers,
    open_anything,
    parse_index_specification,
    sublist,
)

from itertools import cycle, islice
import optparse
import sys

# Known aggregator functions
functions = dict(
    max=max,
    mean=mean,
    mean_sd=mean_sd,
    mean_err=mean_err,
    mean_95ci=mean_95ci,
    median=median,
    min=min,
    sum=sum,
    first=first,
    last=last,
)

# Add metadata for some of the aggregation functions
mean_95ci.argout = ("", "95ci")
mean_err.argout = ("", "err")
mean_sd.argout = ("", "sd")


def create_option_parser():
    """Creates an `OptionParser` that parses the command line
    options."""
    global functions

    def function_callback(option, opt_str, value, parser):
        global functions
        setattr(parser.values, option.dest, functions[value])

    def indexspec_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, parse_index_specification(value))

    parser = optparse.OptionParser(usage=sys.modules[__name__].__doc__.strip())
    parser.add_option(
        "-d",
        "--delimiter",
        metavar="DELIM",
        dest="in_delimiter",
        default="\t",
        help="use DELIM instad of TAB for field delimiter " "in the input file",
    )
    parser.add_option(
        "-D",
        "--output-delimiter",
        metavar="DELIM",
        dest="out_delimiter",
        default="\t",
        help="use DELIM instead of TAB for field delimiter " "in the output file",
    )
    parser.add_option(
        "-f",
        "--fields",
        metavar="LIST",
        dest="fields",
        default=[],
        action="callback",
        type="str",
        callback=indexspec_callback,
        help="use only these columns from the input. The remaining "
        "columns will not be printed.",
    )
    parser.add_option(
        "-F",
        "--function",
        metavar="FUNCTION",
        dest="function",
        default=mean,
        action="callback",
        type="str",
        callback=function_callback,
        help="use the given FUNCTION to aggregate the values. "
        "Possible values are: %s." % ", ".join(sorted(functions.keys())),
    )
    parser.add_option(
        "-m",
        "--mode",
        metavar="MODE",
        dest="mode",
        choices=("column", "multiple"),
        default="multiple",
        help="set the aggregation MODE. Possible values are: column "
        "or multiple. See the documentation for more details.",
    )
    parser.add_option(
        "--strip",
        action="store_true",
        dest="strip",
        default=False,
        help="strip leading and trailing whitespace from each line",
    )

    return parser


def process_files_column(infiles, options):
    """Processes the given files in ``column`` mode.
    
    Files will be processed sequentially. The output is a single line for
    each file where column i contains the result of the aggregation function
    for the column of the file.
    """
    for idx, filename in enumerate(infiles):
        process_files_column_single(open_anything(filename), options, idx == 0)


def process_files_column_single(fp, options, first_file=False):
    """Processes the given stream (open file) in ``column`` mode."""

    # Calculate the column indices we are interested in
    if options.fields:
        col_idxs = [f - 1 for f in options.fields]
    else:
        col_idxs = None

    # Some caching to avoid costly lookups
    delim = options.in_delimiter
    fields = options.fields
    func = options.function
    join = options.out_delimiter.join

    # Set up characters to strip from lines
    chars_to_strip = " \t\r\n" if options.strip else "\r\n"

    # Flag to denote whether we have seen at least one row with numbers.
    # If not, we are still processing the headers.
    data_started = False
    result = []

    for line in fp:
        # Split the input line
        line = line.strip(chars_to_strip).split(delim)

        # Select the relevant columns only
        if col_idxs:
            line = sublist(line, col_idxs)

        if not data_started:
            # Check whether this row contains numbers only (at least in the
            # columns we are interested in)
            if not only_numbers(line):
                # This is a header, print it if we are in the first file, assuming
                # that the remaining files contain the same header
                if first_file:
                    if hasattr(func, "argout"):
                        headers = []
                        for header in line:
                            headers.extend(
                                "%s_%s" % (header, arg) if arg else header
                                for arg in func.argout
                            )
                    else:
                        headers = line
                    print(join(headers))
                continue
            else:
                # Yay, finally real data!
                data_started = True

        # Convert the columns of interest to floats
        line = [float(x) for x in line]
        if len(result) < len(line):
            diff = len(line) - len(result)
            if not result:
                result = [[] for _ in range(diff)]
            else:
                result.extend([0.0] for _ in range(diff))
        for item, l in zip(line, result):
            l.append(item)

    # Print the output
    print(join(list(map(str, flatten(func(items) for items in result)))))


def process_files_multiple(infiles, options):
    """Processes the given files in ``multiple`` mode.
    
    Files will be processed in parallel; row i of each file will be aggregated
    using the aggregation function into row i of the output."""
    # Calculate the column indices we are interested in
    if options.fields:
        col_idxs = [f - 1 for f in options.fields]
    else:
        col_idxs = None

    # Some caching to avoid costly lookups
    delim = options.in_delimiter
    fields = options.fields
    func = options.function
    join = options.out_delimiter.join

    # Flag to denote whether we have seen at least one row with numbers.
    # If not, we are still processing the headers.
    data_started = False

    for lines in zip(*[open_anything(f) for f in infiles]):
        # Split the input line
        lines = [line.strip().split(delim) for line in lines]

        # Select the relevant columns only
        if col_idxs:
            lines = [sublist(line, col_idxs) for line in lines]

        if not data_started:
            # Check whether this row contains numbers only (at least in the
            # columns we are interested in)
            if any(not only_numbers(line) for line in lines):
                # This is a header, print it from the first file, assuming
                # that the remaining files contain the same header
                if hasattr(func, "argout"):
                    headers = []
                    for header in lines[0]:
                        headers.extend(
                            "%s_%s" % (header, arg) if arg else header
                            for arg in func.argout
                        )
                    print(join(headers))
                else:
                    print(join(lines[0]))
                continue
            else:
                # Yay, finally real data!
                data_started = True

        # Convert the columns of interest to floats
        lines = [[float(x) for x in line] for line in lines]

        # Print the output
        row = []
        for items in zip(*lines):
            result = func(items)
            if hasattr(result, "__iter__"):
                row.extend(str(item) for item in result)
            else:
                row.append(str(result))
        print(join(row))


@main_func
def main():
    """Main entry point of the script."""
    parser = create_option_parser()
    options, args = parser.parse_args()

    if options.fields:
        options.fields = list(options.fields)

    if not args:
        parser.error("At least one input file must be given")

    if options.mode == "multiple":
        process_files_multiple(args, options)
    elif options.mode == "column":
        process_files_column(args, options)
    else:
        parser.error("Invalid mode: %s" % options.mode)


if __name__ == "__main__":
    main()

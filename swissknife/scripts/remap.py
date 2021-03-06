#!/usr/bin/env python
# vim:set ts=4 sw=4 sts=4 et:
"""\
Usage: %prog [options] [infile]

Remapping of identifiers in a file using a mapping file or mapping expression.
"""

from swissknife.error import AppError
from swissknife.utils import main_func, open_anything, parse_index_specification

import collections
import optparse
import sys


class SkipRowException(Exception):
    """Exception thrown when we should skip a row from the input
    file."""

    pass


class SkipColumnException(Exception):
    """Exception thrown when we should skip a column from the input
    file."""

    pass


class cautiousdict(dict):
    """Python dict that returns the key itself if the key is not
    found and shows a warning."""

    def __missing__(self, key):
        print("%r not found in mapping" % key, file=sys.stderr)
        return key


class lenientdict(dict):
    """Python dict that returns the key itself if the key is not
    found."""

    def __missing__(self, key):
        return key


class skippingdict(dict):
    """Python dict that throws a specific exception (typically
    `SkipRowException` or `SkipColumnException`) if the key is not
    found."""

    def __init__(self, *args, **kwds):
        if "exc" in kwds:
            self.exc = kwds["exc"]
            del kwds["exc"]
        else:
            self.exc = SkipRowException

    def __missing__(self, key):
        raise self.exc


class universalset(collections.Set):
    """Set-like object that contains every object (even itself)"""

    def __init__(self):
        pass

    def __contains__(self, key):
        return True

    def __iter__(self):
        raise NotImplementedError("cannot iterate over an universal set")

    def __len__(self):
        return float("inf")


class UnknownIDError(AppError):
    """Exception thrown when an unknown ID is found in the input file
    in strict mode."""

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return "unknown ID in input file: {0.key}".format(self)


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
        dest="delimiter",
        default="\t",
        help="use DELIM instad of TAB for field delimiter " "in the input file",
    )
    parser.add_option(
        "-D",
        "--mapping-delimiter",
        metavar="DELIM",
        dest="mapping_delimiter",
        default="\t",
        help="use DELIM instead of TAB for field delimiter " "in the mapping file",
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
        help="remap only these fields",
    )
    parser.add_option(
        "-F",
        "--mapping-fields",
        metavar="OLD,NEW",
        dest="mapping_fields",
        default=[1, 2],
        action="callback",
        type="str",
        callback=indexspec_callback,
        help="use the given columns from the mapping file " "for the old and new IDs",
    )
    parser.add_option(
        "-m",
        "--mapping-file",
        metavar="FILE",
        dest="mapping_file",
        default=None,
        help="load mappings from the given FILE",
    )
    parser.add_option(
        "--mapping-expr",
        metavar="EXPR",
        dest="mapping_expr",
        default=None,
        help="use the given Python expression to calculate the new IDs "
        "instead of a mapping file. Use the variable x to refer to "
        "the old value in the expression",
    )
    parser.add_option(
        "-s",
        "--strict",
        action="store_true",
        dest="strict",
        default=False,
        help="stop when an ID cannot be remapped",
    )
    parser.add_option(
        "-W",
        "--warn",
        action="store_true",
        dest="warn",
        default=False,
        help="print warning for IDs that cannot be remapped",
    )
    parser.add_option(
        "--missing",
        dest="missing_action",
        default="ignore",
        choices=("ignore", "warn", "skip", "fail", "empty"),
        help="specifies what to do when an ID cannot be remapped. "
        "Must be one of ignore (default), warn, skip, empty or fail",
    )
    return parser


def load_mapping(fname, options):
    """Loads a mapping from the given file and returns a dict-like
    object."""
    if options.missing_action == "fail":
        data = {}
    elif options.missing_action == "warn":
        data = cautiousdict()
    elif options.missing_action == "skip":
        data = skippingdict(exc=SkipRowException)
    elif options.missing_action == "empty":
        data = skippingdict(exc=SkipColumnException)
    else:
        data = lenientdict()

    old, new = options.mapping_fields
    old -= 1
    new -= 1
    for row in open_anything(fname):
        parts = row.strip().split(options.mapping_delimiter)
        data[parts[old]] = parts[new]
    return data


def remap_file(infile, mapper, options):
    """Remaps the entries in the given file using the given callable mapper."""
    for line in open_anything(infile):
        parts = line.strip().split(options.delimiter)
        new_parts = []
        skip = False
        for idx, part in enumerate(parts, 1):
            try:
                if idx in options.fields:
                    new_parts.append(mapper(part))
                else:
                    new_parts.append(part)
            except KeyError:
                raise UnknownIDError(part)
            except SkipColumnException:
                pass
            except SkipRowException:
                skip = True
                break
        if not skip:
            print(options.delimiter.join(new_parts))


@main_func
def main():
    """Main entry point of the script."""
    parser = create_option_parser()
    options, args = parser.parse_args()

    if options.strict:
        options.missing_action = "fail"
    elif options.warn:
        options.missing_action = "warn"

    if not options.fields:
        options.fields = universalset()
    else:
        options.fields = set(options.fields)

    if not args:
        args.extend("-")

    if options.mapping_file:
        if len(options.mapping_fields) != 2:
            parser.error("-F must specify exactly two columns")
        mapper = load_mapping(options.mapping_file, options).__getitem__
    elif options.mapping_expr:

        def mapper(value):
            return str(eval(options.mapping_expr, {}, dict(x=value)))

    else:
        parser.error("either -m or --mapping-expr must be given")

    for infile in args:
        remap_file(infile, mapper, options)


if __name__ == "__main__":
    main()

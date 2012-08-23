
from __future__ import division

from datetime import datetime

def first(iterable):
    """Returns the first element of the iterable."""
    for item in iterable:
        return item

def flatten(*args):
    """Recursively flattens a list containing other lists or
    single items into a list.
    
    Examples::

        >>> flatten()
        []
        >>> flatten(2)
        [2]
        >>> flatten(2, 3, 4)
        [2, 3, 4]
        >>> flatten([2, 3, 4])
        [2, 3, 4]
        >>> flatten([[2, 3], [4, 5], 6, [7, 8]])
        [2, 3, 4, 5, 6, 7, 8]
    """
    if len(args) == 0:
        return []
    if len(args) > 1:
        return flatten(list(args))
    if hasattr(args[0], "__iter__") and not isinstance(args[0], basestring):
        return sum(map(flatten, args[0]), [])
    return list(args)

class TableWithHeaderIterator(object):
    """Iterates over rows of a stream that contain a table in tabular format,
    with an optional header."""

    def __init__(self, fp, delimiter=None, every=1, fields=None, strip=False):
        """Creates an iterator that reads the given stream `fp` and uses
        the given `delimiter` character. ``None`` means any whitespace
        character. `fields` specifies which columns to filter on; if it
        is ``None``, all columns will be considered. `strip` specifies
        whether to strip all leading and trailing whitespace from lines
        or not. `every` allows one to specify that only every nth data
        line should be considered from the input file."""
        self.delimiter = delimiter
        self.every = max(1, int(every))
        self.fields = fields
        self.first_column_is_date = False
        self.fp = fp
        self.seen_header = False
        self.strip = bool(strip)
        self.headers = None

    def __iter__(self):
        chars_to_strip = " \t\r\n" if self.strip else "\r\n"
        every = self.every

        line_number = 0
        for line in self.fp:
            parts = line.strip(chars_to_strip).split(self.delimiter)
            if self.fields:
                parts = sublist(parts, self.fields)
            if not parts:
                continue

            if not self.first_column_is_date:
                values = [lenient_float(num) for num in parts]
            else:
                values = [parts[0]] + [lenient_float(num) for num in parts[1:]]

            if not self.seen_header:
                # No data yet, maybe this is the header?
                if any(value is None for value in values):
                    self.headers = parts
                    self.seen_header = True
                    continue

            # This is a real data line. Decide whether to consider it or not.
            if every <= 1 or line_number % every == 0:
                yield values

            line_number += 1


def last(iterable):
    """Returns the last element of the iterable."""
    for item in iterable:
        result = item
    return result

def lenient_float(value, default=None):
    """Like Python's ``float`` but returns the default value when
    the value cannot be converted to a float."""
    try:
        return float(value)
    except ValueError:
        return default

def mask_nans(xs):
    """Replaces None values with NaNs in the given numeric vector and
    then masks all NaNs. Returns a masked NumPy array."""
    from numpy import array, isnan
    from numpy.ma import masked_where
    xs = [x if x is not None else NaN for x in xs]
    xs = array(xs)
    return masked_where(isnan(xs), xs)

def mean(items):
    """Returns the mean of the given items.
    
    Example::
        
        >>> mean([5, 3, 7, 1, 9])
        5.0
    """
    if not items:
        return 0.0
    return sum(items) / len(items)

def mean_sd(items):
    """Returns the mean and the standard deviation of the given items.
    
    Example::
        
        >>> m, sd = mean_sd([5, 3, 7, 1, 9])
        >>> abs(sd - 3.162278) < 1e-5
        True
    """
    m = mean(items)
    if len(items) < 2:
        return m, 0.0

    sqdiff = sum((item-m) ** 2 for item in items)
    return m, (sqdiff / (len(items)-1)) ** 0.5

def median(items):
    """If `items` has an even length, returns the average of the two
    middle elements. If `items` has an odd length, returns the single
    middle element. If `items` is empty, returns ``None``.
    """
    n = len(items)
    if not n:
        return None
    mid = n // 2
    items = sorted(items)
    if n % 2 == 0:
        return (items[mid-1] + items[mid]) / 2
    return float(items[mid])

def only_numbers(iterable):
    """Returns whether the given iterable contains numbers (or strings that
    can be converted into numbers) only."""
    return not any(lenient_float(item) is None for item in iterable)

def open_anything(fname, *args, **kwds):
    """Opens the given file. The file may be given as a file object
    or a filename. If the filename ends in ``.bz2`` or ``.gz``, it will
    automatically be decompressed on the fly. If the filename starts
    with ``http://``, ``https://`` or ``ftp://`` and there is no
    other argument given, the remote URL will be opened for reading.
    A single dash in place of the filename means the standard input.
    """
    if isinstance(fname, file):
        infile = fname
    elif fname == "-" or fname is None:
        import sys
        infile = sys.stdin
    elif (fname.startswith("http://") or fname.startswith("ftp://") or \
         fname.startswith("https://")) and not kwds and not args:
        import urllib2
        infile = urllib2.urlopen(fname)
    elif fname[-4:] == ".bz2":
        import bz2
        infile = bz2.BZ2File(fname, *args, **kwds)
    elif fname[-3:] == ".gz":
        import gzip
        infile = gzip.GzipFile(fname, *args, **kwds)
    else:
        infile = open(fname, *args, **kwds)
    return infile

def parse_date(date_string, format="%Y-%m-%d", default=None, ordinal=False):
    """Parses a string and returns a ``datetime`` instance (when `ordinal` is
    ``False``) or an ordinal number representing the number of days that have
    passed since 0001-01-01 UTC.

    Whenthe date cannot be parsed, the function will return the value of
    `default`. `format` specifies the date format to use."""
    try:
        result = datetime.strptime(date_string, format)
    except TypeError, ValueError:
        return default
    if ordinal:
        return result.toordinal()
    return result

def parse_index_specification(spec):
    """Parses an index specification used as arguments for the -f
    and -F options."""
    result = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = map(int, part.split("-", 1))
            result.extend(xrange(lo, hi+1))
        else:
            result.append(int(part))
    return result

def sublist(l, idxs):
    return [l[i] for i in idxs]


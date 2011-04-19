
from __future__ import division

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

def lenient_float(value, default=None):
    """Like Python's ``float`` but returns the default value when
    the value cannot be converted to a float."""
    try:
        return float(value)
    except ValueError:
        return default

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


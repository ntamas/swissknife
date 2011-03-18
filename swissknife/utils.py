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


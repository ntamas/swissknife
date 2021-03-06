#!/usr/bin/env python
# vim:set ts=4 sw=4 sts=4 et:
"""\
Usage: %prog [options] [infile]

Plots columns from a data file using Matplotlib.
"""

from swissknife.error import AppError
from swissknife.utils import (
    lenient_float,
    main_func,
    mask_nans,
    open_anything,
    parse_date,
    parse_index_specification,
    parse_range_specification,
    parse_size_specification,
    TableWithHeaderIterator,
)

from itertools import cycle, islice, zip_longest
from math import ceil
from numpy import arange, array, isnan, meshgrid, linspace, sqrt, zeros, NaN
from numpy.ma import masked_where
from warnings import warn

import optparse
import re
import sys


DEFAULT_COLORS = "bgrcmyk"
DEFAULT_LINE_STYLES = "- -- -. :".split()
DEFAULT_MARKERS = "os^v<>+*dph8"


def create_option_parser():
    """Creates an `OptionParser` that parses the command line
    options."""

    def gridspec_callback(option, opt_str, value, parser):
        setattr(
            parser.values,
            option.dest,
            parse_size_specification(value, allow_units=False),
        )

    def indexspec_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, parse_index_specification(value))

    def rangespec_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, parse_range_specification(value))

    def sizespec_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, parse_size_specification(value))

    parser = optparse.OptionParser(usage=sys.modules[__name__].__doc__.strip())

    input_group = optparse.OptionGroup(parser, "Input settings")
    input_group.add_option(
        "-d",
        "--delimiter",
        metavar="DELIM",
        dest="delimiter",
        default="\t",
        help="use DELIM instad of TAB for field delimiter " "in the input file",
    )
    input_group.add_option(
        "-D",
        "--dates",
        metavar="AXES",
        dest="dates",
        choices=("none", "x"),
        default="none",
        help="assume that the given AXES contain dates. If AXES=none, "
        "both the X and the Y coordinates will be treated as "
        "numbers. If AXES=x, the X axis will be treated as a "
        "date. Use --date-format to specify the format of the date. "
        "Support for dates on the Y axis may be added later.",
    )
    input_group.add_option(
        "-e",
        "--errorbars",
        metavar="AXES",
        dest="errorbars",
        choices=("none", "y"),
        default="none",
        help="use errorbars on the given AXES. If AXES=none, "
        "no error bars will be used. If AXES=y, every second column "
        "after the 2nd one (i.e. the 3rd, 5th, 7th etc) is assumed to "
        "be an error bar for the value in the previous column. "
        "Default: %default",
    )
    input_group.add_option(
        "-f",
        "--fields",
        metavar="LIST",
        dest="fields",
        default=[],
        action="callback",
        type="str",
        callback=indexspec_callback,
        help="plot only these columns. For line plots (see -t), the "
        "first index must always be the X coordinate, the rest "
        "are Y coordinates of the points and possibly the sizes "
        "of the error bars (if --errorbars is not none). For "
        "3D plots, you need exactly three columns with the "
        "X, Y and Z coordinates.",
    )
    input_group.add_option(
        "--date-format",
        metavar="FORMAT",
        dest="date_format",
        default="%Y-%m-%d",
        help="use the given FORMAT to parse dates. FORMAT is a "
        "format string that must be accepted by datetime.strptime. "
        "Default: %default",
    )
    input_group.add_option(
        "--every",
        metavar="N",
        dest="every",
        default=1,
        help="use only the header and every Nth line from the input file",
    )
    input_group.add_option(
        "--strip",
        action="store_true",
        dest="strip",
        default=False,
        help="strip leading and trailing whitespace from each line",
    )
    parser.add_option_group(input_group)

    output_group = optparse.OptionGroup(parser, "Output settings")
    output_group.add_option(
        "-o",
        "--output",
        metavar="FILE",
        dest="output",
        default=None,
        help="save the output to the given FILE",
    )
    output_group.add_option(
        "-s",
        "--size",
        metavar="WIDTHxHEIGHT",
        dest="size",
        action="callback",
        callback=sizespec_callback,
        type="str",
        default=None,
        help="set the size of the figure to WIDTH x HEIGHT inches. "
        "You may also use cm or mm if you specify it explicitly.",
    )
    output_group.add_option(
        "-t",
        "--type",
        metavar="TYPE",
        dest="type",
        choices=(
            "bar",
            "heatmap",
            "line",
            "quiver",
            "scatter",
            "scatter3d",
            "surface",
            "wireframe",
        ),
        default="line",
        help="the type of plot to draw (bar, heatmap, line, quiver, "
        "scatter, scatter3d, surface or wireframe)",
    )
    output_group.add_option(
        "--font-size",
        metavar="SIZE",
        type=float,
        default=None,
        dest="font_size",
        help="set the font size to SIZE",
    )
    output_group.add_option(
        "--legend",
        dest="legend",
        default="best",
        metavar="LOCATION",
        help="show the legend at the given LOCATION. "
        "Default is 'best'. See the legend location constants in "
        "the legend() function of Matplotlib for more details.",
    )
    output_group.add_option(
        "--no-legend",
        dest="legend",
        action="store_false",
        help="hide the legend from the plot.",
    )
    output_group.add_option(
        "--no-title",
        dest="no_title",
        default=False,
        action="store_true",
        help="show no title at all.",
    )
    output_group.add_option(
        "--scale",
        dest="scale",
        default=1.0,
        metavar="SCALE",
        type=float,
        help="multiply the marker sizes and the line widths by SCALE",
    )
    output_group.add_option(
        "--title",
        metavar="TITLE",
        dest="title",
        default=None,
        help="set the title of the plot to TITLE. "
        "The default title is the input filename.",
    )
    output_group.add_option(
        "--twin",
        dest="twin",
        default=False,
        action="store_true",
        help="use two Y axes if applicable. Odd data "
        "columns will be printed on the first Y axis, even data columns "
        "will be printed on the second Y axis.",
    )
    parser.add_option_group(output_group)

    axis_group = optparse.OptionGroup(parser, "Axis settings")
    axis_group.add_option(
        "--xlabel",
        metavar="LABEL",
        dest="xlabel",
        default="",
        help="set the label of the X axis to LABEL",
    )
    axis_group.add_option(
        "--ylabel",
        metavar="LABEL",
        dest="ylabel",
        default="",
        help="set the title of the Y axis to LABEL",
    )
    axis_group.add_option(
        "--y2label",
        metavar="LABEL",
        dest="y2label",
        default="",
        help="set the title of the second Y axis to LABEL " "(twin axes only)",
    )
    axis_group.add_option(
        "--zlabel",
        metavar="LABEL",
        dest="zlabel",
        default="",
        help="set the title of the Z axis to LABEL (3D plots only)",
    )
    axis_group.add_option(
        "--xrange",
        metavar="MIN:MAX",
        dest="xrange",
        action="callback",
        callback=rangespec_callback,
        type="str",
        default=None,
        help="set the range of the X axis to MIN:MAX",
    )
    axis_group.add_option(
        "--yrange",
        metavar="MIN:MAX",
        dest="yrange",
        action="callback",
        callback=rangespec_callback,
        type="str",
        default=None,
        help="set the range of the Y axis to MIN:MAX",
    )
    axis_group.add_option(
        "--y2range",
        metavar="MIN:MAX",
        dest="y2range",
        action="callback",
        callback=rangespec_callback,
        type="str",
        default=None,
        help="set the range of the second Y axis to MIN:MAX " "(twin axes only)",
    )
    axis_group.add_option(
        "--zrange",
        metavar="MIN:MAX",
        dest="zrange",
        action="callback",
        callback=rangespec_callback,
        type="str",
        default=None,
        help="set the range of the Z axis to MIN:MAX (3D plots only)",
    )
    axis_group.add_option(
        "--xformat",
        metavar="FORMAT",
        dest="xformat",
        default="numeric",
        choices=("numeric", "percentage"),
        help="use the given FORMAT for the X axis labels (numeric or " "percentage)",
    )
    axis_group.add_option(
        "--yformat",
        metavar="FORMAT",
        dest="yformat",
        default="numeric",
        choices=("numeric", "percentage"),
        help="use the given FORMAT for the Y axis labels (numeric or " "percentage)",
    )
    axis_group.add_option(
        "--y2format",
        metavar="FORMAT",
        dest="y2format",
        default="numeric",
        choices=("numeric", "percentage"),
        help="use the given FORMAT for the secondary Y axis labels "
        "(numeric or percentage; twin axes only)",
    )
    axis_group.add_option(
        "--zformat",
        metavar="FORMAT",
        dest="zformat",
        default="numeric",
        choices=("numeric", "percentage"),
        help="use the given FORMAT for the X axis labels (numeric or "
        "percentage; 3D plots only)",
    )
    axis_group.add_option(
        "--no-x-tick-labels",
        dest="show_xticklabels",
        default=True,
        action="store_false",
        help="hide the tick labels on the X axis",
    )
    axis_group.add_option(
        "--no-y-tick-labels",
        dest="show_yticklabels",
        default=True,
        action="store_false",
        help="hide the tick labels on the Y axis",
    )
    axis_group.add_option(
        "--no-y2-tick-labels",
        dest="show_y2ticklabels",
        default=True,
        action="store_false",
        help="hide the tick labels on the second Y axis (twin axes only)",
    )
    axis_group.add_option(
        "--no-z-tick-labels",
        dest="show_zticklabels",
        default=True,
        action="store_false",
        help="hide the tick labels on the Z axis",
    )
    parser.add_option_group(axis_group)

    heatmap_group = optparse.OptionGroup(parser, "Heatmap settings")
    heatmap_group.add_option(
        "--colormap",
        metavar="COLORMAP",
        default=None,
        type=str,
        dest="colormap",
        help="set the colormap to COLORMAP. Use the "
        "Matplotlib colormap names here (e.g., hot, spectral).",
    )
    heatmap_group.add_option(
        "--contours",
        default=False,
        action="store_true",
        dest="contours",
        help="show the contour lines on the plot",
    )
    heatmap_group.add_option(
        "--contour-labels",
        default=False,
        action="store_true",
        dest="contour_labels",
        help="show the contour line labels on the plot. " "Implies --contours",
    )
    heatmap_group.add_option(
        "--grid-size",
        metavar="WIDTHxHEIGHT",
        dest="grid_size",
        default=(50, 50),
        action="callback",
        callback=gridspec_callback,
        type="str",
        help="set the size of the grid on which the heatmap is drawn "
        "to WIDTHxHEIGHT. The default is 50x50.",
    )
    heatmap_group.add_option(
        "--interpolate",
        default=None,
        dest="interpolate",
        metavar="METHOD",
        help="use the given interpolation METHOD when "
        "drawing the heatmap. See the Matplotlib API of the "
        "imshow() function for more details.",
    )
    heatmap_group.add_option(
        "--no-colorbar",
        default=True,
        action="store_false",
        dest="colorbar",
        help="don't show colorbar on heatmap plots.",
    )
    parser.add_option_group(heatmap_group)

    return parser


def interpolate_to_regular_grid(xs, ys, zs, options):
    """Interpolates irregularly spaced three-dimensional data to a regular
    grid. The grid size is determined by `options.grid_size`."""
    from matplotlib.mlab import griddata

    grid_size = options.grid_size
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    tries = 3
    zi = None

    while True:
        xi = linspace(min_x, max_x, num=int(grid_size[0]))
        yi = linspace(min_y, max_y, num=int(grid_size[1]))
        try:
            zi = griddata(xs, ys, array(zs), xi, yi, interp="linear")
            break
        except ValueError as err:
            if err.message and err.message.startswith(
                "output grid must have constant spacing"
            ):
                # We do have constant spacing but it is inaccurate. Try
                # doubling the grid size
                grid_size = grid_size[0] * 2, grid_size[1] * 2
                tries -= 1
                if tries <= 0:
                    # Give up
                    break

    if zi is None:
        # Okay, we gave up, let's just use nearest neighbor
        # interpolation with the original grid size
        xi = linspace(min_x, max_x, num=int(options.grid_size[0]))
        yi = linspace(min_y, max_y, num=int(options.grid_size[1]))
        zi = griddata(xs, ys, array(zs), xi, yi, interp="nn")
        warn(
            "Using nearest neighbor interpolation instead of "
            "linear; watch out for artifacts if the X and "
            "Y ranges are wildly different"
        )

    return xi, yi, zi


def plot_file_on_figure(infile, figure, options):
    """Plots the dataset in the given file on the given figure."""
    iterator = TableWithHeaderIterator(
        open_anything(infile),
        delimiter=options.delimiter,
        every=options.every,
        fields=options.fields,
        strip=options.strip,
    )
    iterator.first_column_is_date = "x" in options.dates
    func = globals()["plot_%s_from_table_iterator" % options.type]
    func(iterator, figure, options)

    # Add the title
    if not options.no_title:
        if options.title is None:
            if infile != "-":
                figure.suptitle(infile)
        else:
            figure.suptitle(options.title)


def set_axis_ranges(primary_axes, secondary_axes, options):
    """Sets the ranges of the primary and secondary axes using the options
    given in `options`."""
    if options.xrange:
        primary_axes.set_xlim(*options.xrange)
    if options.yrange:
        primary_axes.set_ylim(*options.yrange)
    if options.zrange and hasattr(primary_axes, "set_zlim"):
        primary_axes.set_zlim(*options.zrange)
    if secondary_axes and options.y2range:
        secondary_axes.set_ylim(*options.y2range)


def add_axis_titles(primary_axes, secondary_axes, options):
    """Adds the titles on the given primary and secondary axes using the
    options given in `options`."""
    # Add the axis titles
    if options.xlabel:
        primary_axes.set_xlabel(options.xlabel)
    if options.ylabel:
        primary_axes.set_ylabel(options.ylabel)
    if options.zlabel and hasattr(primary_axes, "set_zlabel"):
        primary_axes.set_zlabel(options.zlabel)
    if secondary_axes and options.y2label:
        secondary_axes.set_ylabel(options.y2label)


def get_axis_formatter_for_format(format):
    """Returns an axis formatter suitable for the given ``format``."""
    from matplotlib.ticker import FuncFormatter, ScalarFormatter

    if format == "numeric":
        return ScalarFormatter()
    elif format == "percentage":

        def percent_format(x, _):
            return "%d%%" % int(round(x * 100))

        return FuncFormatter(percent_format)
    else:
        raise KeyError("no such axis format: %s" % format)


def set_axis_formatters(primary_axes, secondary_axes, options):
    """Sets the tick label formatters for the given primary and secondary
    axes using the options given in `options`."""

    if options.xformat:
        formatter = get_axis_formatter_for_format(options.xformat)
        primary_axes.xaxis.set_major_formatter(formatter)
    if options.yformat:
        formatter = get_axis_formatter_for_format(options.yformat)
        primary_axes.yaxis.set_major_formatter(formatter)
    if options.zformat and hasattr(primary_axes, "zaxis"):
        formatter = get_axis_formatter_for_format(options.zformat)
        primary_axes.zaxis.set_major_formatter(formatter)
    if secondary_axes and options.y2format:
        formatter = get_axis_formatter_for_format(options.y2format)
        secondary_axes.yaxis.set_major_formatter(formatter)


def set_axis_ticks(primary_axes, secondary_axes, options):
    """Hides or shows the axis ticks based on the options given in
    `options`."""
    if not options.show_xticklabels:
        primary_axes.set_xticklabels([])
    if not options.show_yticklabels:
        primary_axes.set_yticklabels([])
    if not options.show_zticklabels:
        primary_axes.set_zticklabels([])
    if secondary_axes and not options.show_y2ticklabels:
        secondary_axes.set_yticklabels([])


def setup_axes(axes, options):
    """Sets all the relevant axis properties using the options given
    in `options`."""
    if hasattr(axes, "__len__"):
        primary_axis = axes[0]
        secondary_axis = axes[1] if len(axes) > 1 else None
    else:
        primary_axis, secondary_axis = axes, None

    add_axis_titles(primary_axis, secondary_axis, options)
    set_axis_formatters(primary_axis, secondary_axis, options)
    set_axis_ranges(primary_axis, secondary_axis, options)
    set_axis_ticks(primary_axis, secondary_axis, options)


def setup_legend(all_axes, legend_handles, legend_labels, options):
    """Sets all the relevant legend properties using the options given
    in `options`."""
    if not options.legend or not legend_labels:
        return

    legend_axis = all_axes[-1]

    if options.twin and options.legend == "best":
        # We have two Y axes. The problem is that the "best placement"
        # algorithm in Matplotlib takes into account only the contents
        # of the axis on which the legend is placed. We fix that here.
        # This is terrible monkey-patching but we cannot do any better.
        from matplotlib.legend import Legend

        tmp_legend = all_axes[0].legend(legend_handles, legend_labels)
        tmp_data = tmp_legend._auto_legend_data()
        all_axes[0].legend_ = None
        del tmp_legend

        old_func = Legend._auto_legend_data

        def patched_auto_legend_data(self):
            super_data = old_func(self)
            for idx, item in enumerate(super_data):
                item += tmp_data[idx]
            return super_data

        Legend._auto_legend_data = patched_auto_legend_data
    else:
        old_func = None

    legend_obj = legend_axis.legend(legend_handles, legend_labels, loc=options.legend)
    legend_obj.get_frame().set_alpha(0.75)

    # if old_func is not None:
    #     Legend._auto_legend_data = old_func


def parse_headers(headers):
    """Iterates over the headers of the input file and tries to
    extract style specifications out of them.

    A header contains a style specification if it ends with a substring in
    double square brackets (i.e. ``[[...]]``). This function will return
    two lists. The first contains the header strings *without* the style
    specifications (if there were any), the second contains the style
    specifications themselves or ``None`` if a header did not have a style
    specification at all."""
    if headers is None:
        return None, []

    new_headers, specs = [], []
    rex = re.compile(r"(.*)\[\[([^\]]+)]]$")
    for header in headers:
        match = rex.match(header)
        if match:
            new_headers.append(match.group(1).strip())
            specs.append(match.group(2))
        else:
            new_headers.append(header)
            specs.append(None)
    return new_headers, specs


def plot_bar_from_table_iterator(table_iterator, figure, options):
    """Plots the dataset whose rows will be yielded by the given
    `table_iterator` (an instance of `TableWithHeaderIterator`)
    using bar plots. The plot will be drawn on `figure`."""
    yss = []
    for values in table_iterator:
        # Less than one value? If so, skip this line.
        if len(values) < 1:
            continue

        # Not enough columns? Add the missing ones.
        if len(values) < len(yss):
            values.extend([None] * (len(yss) - len(values)))

        # For the time being, we put everything in yss and
        # will separate them later into Y coordinates and
        # error bars if options.errorbars is not none
        if not yss:
            # First row, must extend yss with columns
            yss = [[y] for y in values]
        else:
            for ys, y in zip(yss, values):
                ys.append(y)

    headers, style_overrides = parse_headers(table_iterator.headers)

    # Calculate the legend labels
    legend_handles, legend_labels = [], []
    if yss and headers is not None:
        legend_labels = headers[:]

    # Mask NaNs in yss
    yss = [[y if y is not None else NaN for y in ys] for ys in yss]
    yss = array(yss)
    yss = masked_where(isnan(yss), yss)

    # Handle error bars
    if options.errorbars == "y":
        # Separate the error bars from the values
        ncol = len(yss)
        errorbars = yss[1::2]
        yss = yss[::2]
        legend_labels = legend_labels[: min(len(legend_labels), ncol) : 2]
    else:
        # No error bars
        errorbars = None

    # Set up the colors to be used
    colors = DEFAULT_COLORS
    styles = list(colors)

    # Override the line styles where the header says so
    for idx, override in enumerate(style_overrides[1:]):
        if override is not None:
            styles[idx] = override

    # Set up the list of axes we will use
    all_axes = [figure.gca()]
    if options.twin:
        all_axes.append(figure.gca().twinx())

    # Plot the bars
    xs = arange(0, len(yss[0]))
    bottoms = zeros(len(yss[0]))
    i = 0
    for axes, style, ys in zip(cycle(all_axes), cycle(styles), yss):
        params = dict(left=xs, height=ys, bottom=bottoms, color=style)
        if errorbars is not None:
            params["yerr"] = errorbars[i]
            i += 1

        handle = axes.bar(**params)
        legend_handles.append(handle[0])

        bottoms += ys

    # Set up the axes
    setup_axes(all_axes, options)

    # Add the legend
    setup_legend(all_axes, legend_handles, legend_labels, options)


def plot_heatmap_from_table_iterator(table_iterator, figure, options):
    """Plots a heatmap whose X-Y coordinates and Z values come from the given
    `table_iterator`. The plot will be drawn on `figure`."""

    xs, ys, zs = [], [], []
    for values in table_iterator:
        # Less than three values? If so, skip this line.
        if len(values) < 3:
            continue
        # Any of the values missing? If so, skip this line
        if any(value is None for value in values):
            continue
        # Store the values
        xs.append(values[0])
        ys.append(values[1])
        zs.append(values[2])

    # Create a regular grid
    xi, yi, zi = interpolate_to_regular_grid(xs, ys, zs, options)

    # Show the image
    axes = figure.gca()
    kwds = dict(
        cmap=options.colormap,
        interpolation=options.interpolate,
        extent=(xi[0], xi[-1], yi[0], yi[-1]),
        aspect="auto",
        origin="lower",
    )
    if options.zrange is not None:
        kwds.update(vmin=options.zrange[0], vmax=options.zrange[1])
    image = axes.imshow(zi, **kwds)

    # Show the contour plot if needed
    if options.contours:
        contours = axes.contour(xi, yi, zi, colors="k")
        if options.contour_labels:
            axes.clabel(contours, inline=1)

    # Show the color bar
    if options.colorbar:
        formatter = get_axis_formatter_for_format(options.zformat)
        colorbar = figure.colorbar(image, format=formatter)

    # Set up the axes
    setup_axes(axes, options)

    return figure


def plot_line_from_table_iterator(table_iterator, figure, options):
    """Plots the dataset whose rows will be yielded by the given
    `table_iterator` (an instance of `TableWithHeaderIterator`).
    The plot will be drawn on `figure`."""
    xs, yss = [], []
    for values in table_iterator:
        # Less than two values? If so, skip this line.
        if len(values) < 2:
            continue

        # Not enough columns? Add the missing ones.
        if len(values) < len(yss) + 1:
            values.extend([None] * (len(yss) + 1 - len(values)))

        # The first value is the X coordinate. We put the
        # rest in yss and will separate them later into Y
        # coordinates and error bars if options.errorbars
        # is not none
        xs.append(values[0])
        if not yss:
            # First row, must extend yss with columns
            yss = [[y] for y in islice(values, 1, None)]
        else:
            for ys, y in zip(yss, islice(values, 1, None)):
                ys.append(y)

    headers, style_overrides = parse_headers(table_iterator.headers)

    # Calculate the legend labels
    legend_handles, legend_labels = [], []
    if yss and headers is not None:
        legend_labels = headers[1:]

    # If the x axis contains dates, map them to dates since 0001-01-01 UTC
    # since Matplotlib requires this
    if options.dates == "x" or options.dates == "xy":
        xs = [
            parse_date(x, format=options.date_format, default=NaN, ordinal=True)
            for x in xs
        ]

    # Mask NaNs in xs
    xs = mask_nans(xs)

    # Mask NaNs in yss
    yss = [[y if y is not None else NaN for y in ys] for ys in yss]
    yss = array(yss)
    yss = masked_where(isnan(yss), yss)

    # Handle error bars
    if options.errorbars == "y":
        # Separate the error bars from the values
        ncol = len(yss)
        errorbars = yss[1::2]
        yss = yss[::2]
        legend_labels = legend_labels[: min(len(legend_labels), ncol) : 2]
    else:
        # No error bars
        errorbars = None

    # Set up the line styles to be used
    colors = DEFAULT_COLORS
    styles = DEFAULT_LINE_STYLES
    line_styles = [color + style for style in styles for color in colors]
    bar_styles = [color + "o" for style in styles for color in colors]

    # Override the line styles where the header says so
    for idx, override in enumerate(style_overrides[1:]):
        if override is not None:
            line_styles[idx] = override
            bar_styles[idx] = override

    # Set up the list of axes we will use
    all_axes = [figure.gca()]
    if options.twin:
        all_axes.append(figure.gca().twinx())

    # Calculate the desired sizes factor from the figure width
    size_scale_factor = options.scale
    marker_size = 6.0 * size_scale_factor
    cap_size = 3.0 * size_scale_factor
    line_width = size_scale_factor
    kwargs = dict(markersize=marker_size, linewidth=line_width)

    # Plot the lines
    for axes, style, ys in zip(cycle(all_axes), cycle(line_styles), yss):
        if options.dates != "none":
            handle = axes.plot_date(xs, ys, style, **kwargs)
        else:
            handle = axes.plot(xs, ys, style, **kwargs)
        legend_handles.append(handle[0])

    # Plot the error bars if needed
    if errorbars is not None:
        # First decide the frequency of markers so they don't overlap with
        # each other
        total_marker_width_inches = len(xs) * marker_size / 72.0
        marker_freq = int(ceil(total_marker_width_inches * 2 / figure.get_figwidth()))

        # Now plot the error bars
        for axes, style, ys, yerrs in zip(
            cycle(all_axes), cycle(bar_styles), yss, errorbars
        ):
            # Subsample xs and ys if needed -- markevery would subsample the
            # markers only but not the error bars
            if marker_freq > 1:
                xs_s, ys_s = xs[::marker_freq], ys[::marker_freq]
                yerrs_s = yerrs[::marker_freq]
            else:
                xs_s, ys_s, yerrs_s = xs, ys, yerrs
            axes.errorbar(
                xs_s, ys_s, yerr=yerrs_s, fmt=style, capsize=cap_size, **kwargs
            )

    # Set up the axes
    setup_axes(all_axes, options)

    # Add the legend
    setup_legend(all_axes, legend_handles, legend_labels, options)


def plot_quiver_from_table_iterator(table_iterator, figure, options):
    """Plots a 2D quiver plot (a.k.a. vector field) whose points come from the
    given `table_iterator`. The plot will be drawn on `figure`."""

    xs, ys, us, vs = [], [], [], []
    for values in table_iterator:
        # Less than two values? If so, skip this line.
        if len(values) < 2:
            continue
        # Pad the values with zeros up to length 4
        if len(values) < 4:
            values += [0.0] * (4 - len(values))
        # Any of the values missing? If so, skip this line
        if any(value is None for value in values):
            continue
        # Store the values
        xs.append(values[0])
        ys.append(values[1])
        us.append(values[2])
        vs.append(values[3])

    # Mask NaNs in us and vs. Matplotlib does not support masks in
    # xs or ys
    us = mask_nans(us)
    vs = mask_nans(vs)
    grads = sqrt(us * us + vs * vs)

    # Get the axes
    axes = figure.gca()

    # Plot the gradient contours
    if options.contours:
        xi, yi, gi = interpolate_to_regular_grid(xs, ys, grads, options)
        contours = axes.contour(xi, yi, gi)
        if options.contour_labels:
            axes.clabel(contours, inline=1)

    # Plot the quiver plot
    axes.quiver(xs, ys, us, vs, angles="xy", pivot="tail", color="blue")

    # Set up the axes
    setup_axes(axes, options)

    return figure


def plot_scatter_from_table_iterator(table_iterator, figure, options):
    """Plots a 2D scatterplot whose points come from the given `table_iterator`.
    The plot will be drawn on `figure`."""

    xss, yss = [], []
    for values in table_iterator:
        # Odd number of columns? If so, skip this line.
        if len(values) % 2 != 0:
            continue

        # Not enough columns? Add the missing ones
        if len(values) < len(xss) * 2:
            values.extend([None] * (len(xss) * 2 - len(values)))

        # Values come in X-Y pairs. When X is None, we skip the
        # corresponding Y value. Similarly, when Y is None, we skip
        # the corresponding X value. First, we iterate over values
        # and make sure that Y is None iff X is None
        for index in range(len(values)):
            if values[index] is None:
                values[index ^ 1] = None

        # Now we can store the X-Y pairs, skipping None values
        if not xss:
            # First row, must extend xss and yss with columns
            xss = [[x] if x is not None else [] for x in islice(values, 0, None, 2)]
            yss = [[y] if y is not None else [] for y in islice(values, 1, None, 2)]
        else:
            for xs, x in zip(xss, islice(values, 0, None, 2)):
                if x is not None:
                    xs.append(x)
            for ys, y in zip(yss, islice(values, 1, None, 2)):
                if y is not None:
                    ys.append(y)

    headers, style_overrides = parse_headers(table_iterator.headers)

    # Calculate the legend labels
    legend_handles, legend_labels = [], []
    if yss and headers is not None:
        legend_labels = headers[::2]

    # Strip suffixes and prefixes from the end of the legend labels
    new_labels = []
    suffixes = ["_x", " x", "(x)"]
    prefixes = ["x_", "x "]
    for label in legend_labels:
        for prefix in prefixes:
            if label.startswith(prefix):
                label = label[len(prefix) :]
                break
        for suffix in suffixes:
            if label.endswith(suffix):
                label = label[: -len(suffix)]
                break
        new_labels.append(label.strip())
    legend_labels = new_labels

    # Set up the marker styles to be used
    colors = DEFAULT_COLORS
    styles = list(colors)

    # Override the line styles where the header says so
    for idx, override in enumerate(style_overrides[1:]):
        if override is not None:
            styles[idx] = override

    # Create the axes
    axes = figure.gca()
    all_axes = [axes]

    # Plot the scatterplot
    for xs, ys, style in zip(xss, yss, cycle(styles)):
        handle = axes.scatter(xs, ys, c=style)
        legend_handles.append(handle)

    # Set up the axes
    setup_axes(all_axes, options)

    # Add the legend
    setup_legend(all_axes, legend_handles, legend_labels, options)

    return figure


def plot_scatter3d_from_table_iterator(table_iterator, figure, options):
    """Plots a 3D scatterplot whose points come from the given `table_iterator`.
    The plot will be drawn on `figure`."""

    xs, ys, zs = [], [], []
    for values in table_iterator:
        # Less than three values? If so, skip this line.
        if len(values) < 3:
            continue
        # Any of the values missing? If so, skip this line
        if any(value is None for value in values):
            continue
        # Store the values
        xs.append(values[0])
        ys.append(values[1])
        zs.append(values[2])

    # Import 3D axes
    from mpl_toolkits.mplot3d import Axes3D

    # Create the axes
    axes = Axes3D(figure)

    # Plot the scatterplot
    axes.scatter(xs, ys, zs)

    # Set up the axes
    setup_axes(axes, options)

    return figure


def plot_surface_from_table_iterator(table_iterator, figure, options, wireframe=False):
    """Plots a 3D surface whose points come from the given `table_iterator`.
    The plot will be drawn on `figure`."""

    xs, ys, zdict = set(), set(), {}
    for values in table_iterator:
        # Less than three values? If so, skip this line.
        if len(values) < 3:
            continue
        # Any of the values missing? If so, skip this line
        if any(value is None for value in values):
            continue
        # Store the values
        xs.add(values[0])
        ys.add(values[1])
        zdict[values[0], values[1]] = values[2]

    # Create the mesh grid and fill the Z values
    xs, ys = sorted(xs), sorted(ys)
    zs = zeros((len(xs), len(ys)))
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            zs[i, j] = zdict.get((x, y), NaN)
    ys, xs = meshgrid(sorted(ys), sorted(xs))
    zs = masked_where(isnan(zs), zs)
    # Use the minimum value instead of NaNs -- this is because Matplotlib
    # won't apply the colormap if there are NaNs in the data
    zs = zs.filled(zs.min())

    # Import 3D axes
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib import cm

    # Create the axes
    axes = Axes3D(figure)

    # Plot the surface
    if wireframe:
        axes.plot_wireframe(xs, ys, zs)
    else:
        axes.plot_surface(xs, ys, zs, rstride=1, cstride=1, cmap=cm.jet)

    # Set up the axes
    setup_axes(axes, options)

    return figure


def plot_wireframe_from_table_iterator(table_iterator, figure, options):
    """Plots a 3D  whose points come from the given `table_iterator`.
    The plot will be drawn on `figure`."""
    return plot_surface_from_table_iterator(
        table_iterator, figure, options, wireframe=True
    )


@main_func
def main():
    """Main entry point of the script."""
    import matplotlib

    parser = create_option_parser()
    options, args = parser.parse_args()

    # Do we need headless mode for matplotlib?
    if options.output:
        matplotlib.use("agg")

    if options.fields:
        options.fields = [field - 1 for field in options.fields]

    if not options.size:
        options.size = (8.0, 6.0)

    if options.font_size:
        matplotlib.rcParams.update({"font.size": options.font_size})

    if options.legend:
        options.legend = options.legend.lower().replace("_", " ")
        if options.legend == "none" or options.legend == "hide":
            options.legend = None

    if not args:
        args.extend("-")

    from matplotlib import pyplot as plt

    figure = plt.figure(figsize=options.size)

    for infile in args:
        plot_file_on_figure(infile, figure, options)

    if options.output:
        plt.savefig(options.output)
    else:
        plt.show()


if __name__ == "__main__":
    main()

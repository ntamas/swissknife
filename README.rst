==========
swissknife
==========
--------------------------------------------------
A collection of handy utilities for data crunching
--------------------------------------------------

:Author: Tamas Nepusz

Rationale
=========

One thing I found myself doing all the time when crunching bioinformatics
data is to map a tabular data file (say, a set of proteins and their
properties) from one ID scheme to another. This is a fairly simple task
and it can be coded in only a few lines in Python, but still, it's
annoying to do it every time I'm faced with a new dataset with a new
ID scheme. So I decided to wrap up a simple generic Python script that
does this and nothing else. Then I realized that probably I will have
tons of these simple utility scripts lying around in hidden corners of
my hard drive, and that many other researchers around the world are
probably doing the same and are probably wrapping up similar simple
scripts to solve similar simple tasks, needlessly wasting time and
effort. So I decided to make this small set of utilities completely
public.

Script index
============

``aggregate``
    Suppose that you are running some randomized simulation of a dynamic
    process on your computer and log the state of some variables at each
    time step *t*. You are generally interested in the average behaviour
    of the system at each time step *t*, therefore you run the simulation
    1000 times and save the results to 1000 different files. ``aggregate``
    helps you get the average behaviour in an 1001th data file by
    taking the mean of values in row *i* and column *j* across each of your
    1000 files. It is also capable of recognizing headers in the input
    files; these will be printed intact to the output file.

``groupby``
    Takes a tabular input file where one of the columns is considered
    a primary key, and collects entries in each row with the same
    primary key into a single row in the output file.

``remap``
    Script that can be used to remap columns of entries in a text file
    based on an external mapping file that maps old entry values to new
    ones, or based on a mapping expression specified on the command line.

``qplot``
    Plotting script for taking a quick look at the columns of a text file
    on a 2D plot.

Bugs, questions?
================

Have you found a bug in the code? Do you have questions? Let me know.
I think you are smart enough to figure out my email address by Googling
for my name. Or just drop me a message on Github.

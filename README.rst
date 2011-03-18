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
for my name.

#!/usr/bin/env python

import argparse
import os
from nexusbuilder import NexusBuilder

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='This script builds a nexus file from a specified IDF file', prog='builder')
    positional_args = parser.add_argument_group('Positional arguments')
    positional_args.add_argument(
        'IDF', nargs='?',
        help='The path to the idf file to load')
    optional_args = parser.add_argument_group('Optional arguments')
    optional_args.add_argument('-p', '--plot', action='store_true', default=False,
                               help='Plots the geometry in the DetectorPlotter')
    optional_args.add_argument('-d', '--outputdirectory', default=None,
                               help='The output directory where the generated nexus file should go')
    optional_args.add_argument('-f', '--outputfilename', default=None,
                               help='The filename desired for the generated nexus file')

    arguments = parser.parse_args()

    if not os.path.exists(arguments.IDF):
        raise ValueError('Specified IDF {} does not exist'.format(arguments.IDF))

    output_dir = arguments.outputdirectory if arguments.outputdirectory else os.path.dirname(
        os.path.realpath(arguments.IDF))
    output_filename = arguments.outputfilename if arguments.outputfilename else \
    os.path.splitext(os.path.basename(arguments.IDF))[0] + '.hdf5'

    with NexusBuilder(os.path.join(output_dir, output_filename), idf_file=arguments.IDF, compress_type='gzip',
                      compress_opts=1) as builder:
        builder.add_instrument_geometry_from_idf()

    if arguments.plot:
        from detectorplotter import DetectorPlotter

        with DetectorPlotter(output_filename) as plotter:
            plotter.plot_pixel_positions()

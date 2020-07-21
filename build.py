#!/usr/bin/env python

import argparse
import os
from nexusutils.nexusbuilder import NexusBuilder
from nexusutils.nexustooff import nexus_geometry_to_off_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This script builds a nexus file from a specified IDF file",
        prog="builder",
    )
    positional_args = parser.add_argument_group("Positional arguments")
    positional_args.add_argument(
        "IDF", nargs="?", help="The path to the idf file to load"
    )
    optional_args = parser.add_argument_group("Optional arguments")
    optional_args.add_argument(
        "-p",
        "--plot",
        action="store_true",
        default=False,
        help="Plots the geometry in the DetectorPlotter",
    )
    optional_args.add_argument(
        "-d",
        "--output-directory",
        default=None,
        help="The output directory where the generated NeXus file should go",
    )
    optional_args.add_argument(
        "-f",
        "--output-filename",
        default=None,
        help="The filename desired for the generated NeXus file",
    )
    optional_args.add_argument(
        "-o",
        "--off-filename",
        default=None,
        help="Creates OFF file of full geometry with this filename",
    )
    optional_args.add_argument(
        "-r",
        "--render",
        action="store_true",
        default=False,
        help="Render 3D view of output OFF file, must be used with -o",
    )
    optional_args.add_argument(
        "-c",
        "--compress-type",
        default="gzip",
        help="Specify compression type for NeXus file (gzip, szip, none, ...)",
    )

    arguments = parser.parse_args()

    if not os.path.exists(arguments.IDF):
        raise ValueError("Specified IDF {} does not exist".format(arguments.IDF))

    output_dir = (
        arguments.output_directory
        if arguments.output_directory
        else os.path.dirname(os.path.realpath(arguments.IDF))
    )
    output_filename = (
        arguments.output_filename
        if arguments.output_filename
        else os.path.splitext(os.path.basename(arguments.IDF))[0] + ".hdf5"
    )
    nexus_file_fullpath = os.path.join(output_dir, output_filename)

    compress_options = None
    if arguments.compress_type is "gzip":
        compress_options = 1
    elif arguments.compress_type is "none":
        arguments.compress_type = None
    with NexusBuilder(
        nexus_file_fullpath,
        idf_file=arguments.IDF,
        compress_type=arguments.compress_type,
        compress_opts=compress_options,
    ) as builder:
        builder.add_instrument_geometry_from_idf()

    if arguments.plot:
        from nexusutils.detectorplotter import DetectorPlotter

        with DetectorPlotter(output_filename) as plotter:
            plotter.plot_pixel_positions()

    if arguments.off_filename:
        off_file_fullpath = os.path.join(output_dir, arguments.off_filename)
        nexus_geometry_to_off_file(nexus_file_fullpath, off_file_fullpath)
        if arguments.render:
            from nexusutils.drawoff import render_off_from_file

            render_off_from_file(off_file_fullpath)

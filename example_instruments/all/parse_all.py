from nexusbuilder import NexusBuilder
import os

if __name__ == '__main__':
    passes = 0
    failures = 0
    for file in os.listdir("/home/jonmd/git/python-nexus-utils/example_instruments/all"):
        if file.endswith(".xml"):
            output_filename = file[:-4] + ".hdf5"

            builder = NexusBuilder(output_filename, idf_file=file, compress_type='gzip', compress_opts=1)

            try:
                detectors_added = builder.add_instrument_geometry_from_idf()
                if detectors_added:
                    passes += 1
            except:
                failures += 1

    percent_pass = '%s' % float('%.3g' % ((100. / (passes + failures)) * passes))
    print(percent_pass + "% of all (" + str(passes + failures) +
          ") IDFs for which parsing was attempted resulted in NeXus files with at least one detector")

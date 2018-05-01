import h5py
from tabulate import tabulate
from operator import itemgetter
import numpy as np
import seaborn
import matplotlib.pylab as pl
import os


class HDF5SizeProfiler:
    def __init__(self, filename):
        self.source_file = h5py.File(filename, 'r')
        self.file_size = os.path.getsize(filename)
        self.datasets = []

        def __visitor_func(name, node):
            if isinstance(node, h5py.Dataset):
                # node is a dataset
                data_size = node.size * node.dtype.itemsize
                datatype = str(node.dtype)
                if datatype[:2] == '|S':
                    datatype = 'str'
                self.datasets.append({'Dataset name': name, 'Datatype': datatype, 'Size (elements)': node.size,
                                      'Size (bytes)': data_size})

        # NB it doesn't visit nodes which are any kind of link
        self.source_file.visititems(__visitor_func)

        self.total_bytes = np.sum(list([dataset['Size (bytes)'] for dataset in self.datasets]))
        size_factor = 100. / self.total_bytes
        for dataset in self.datasets:
            dataset['% of total size'] = dataset['Size (bytes)'] * size_factor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.source_file is not None:
            self.source_file.close()

    def print_stats_table(self):
        print('Total uncompressed size is {0} megabytes, compressed file size is {1} megabytes'
              .format(self.total_bytes / 1000000., self.file_size / 1e6))

        datasets_sorted_by_size = sorted(self.datasets, key=itemgetter('Size (bytes)'), reverse=True)
        print(tabulate(datasets_sorted_by_size, headers='keys'))

    def draw_pie_chart(self):
        plot_data = list([[dataset['% of total size'], dataset['Dataset name']] for dataset in self.datasets if
                          dataset['% of total size'] > 1.])
        values = np.array(plot_data)[:, 0]
        names = np.array(plot_data)[:, 1]
        pl.pie(values, labels=names, autopct='%1.1f%%', shadow=True, startangle=90)
        pl.show()


if __name__ == '__main__':
    # Example usage
    with HDF5SizeProfiler('example_instruments/sans2d/SANS2D_example.hdf5') as profiler:
        profiler.print_stats_table()
        profiler.draw_pie_chart()

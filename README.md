# python-nexus-utilities
Functions to assist with building example NeXus files in the proposed format for ESS from existing NeXus files and Mantid IDFs.

Tested with Python 3.5. You can install dependencies with
```
pip install -r requirements.txt
```

## Examples

Examples can be found in the `example_instruments` directory. Example scripts should be run from their own directory with the root directory of the repository in `PYTHONPATH` (IDEs such as PyCharm do this by default).

- `python SANS2D_example.py` runs an example using a NeXus file and Mantid instrument definition from the SANS2D instrument. This outputs a new NeXus file in the proposed new format and contains examples of the `NXshape` and `NXgrid_pattern` groups.

- `python LOKI_example.py` runs an example using a Mantid IDF for the LOKI instrument. It shows examples of the proposed `NXgrid_shape` group. 

## Development

Unit tests can be run with
```
pytest
```

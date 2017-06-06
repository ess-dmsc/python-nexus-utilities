# python-nexus-utilities
Functions to assist with building example NeXus files from existing ones.

Tested with Python 3.5. You can install dependencies with
```
pip install -r requirements.txt
```

`python example_instruments/sans2d/SANS2D_example.py` runs an example using a NeXus file and Mantid instrument definition from the SANS2D instrument. This outputs a new NeXus file in the proposed new format and contains examples of the `NXshape` and `NXgrid_pattern` groups.

`python example_instruments/loki/LOKI_example.py` runs an example using a Mantid IDF for the LOKI instrument. It shows examples of the proposed `NXgrid_shape` group. 

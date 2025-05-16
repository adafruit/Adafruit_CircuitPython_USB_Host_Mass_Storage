Introduction
============


.. image:: https://readthedocs.org/projects/adafruit-circuitpython-usb-host-mass-storage/badge/?version=latest
    :target: https://docs.circuitpython.org/projects/usb-host-mass-storage/en/latest/
    :alt: Documentation Status


.. image:: https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/main/badges/adafruit_discord.svg
    :target: https://adafru.it/discord
    :alt: Discord


.. image:: https://github.com/adafruit/Adafruit_CircuitPython_USB_Host_Mass_Storage/workflows/Build%20CI/badge.svg
    :target: https://github.com/adafruit/Adafruit_CircuitPython_USB_Host_Mass_Storage/actions
    :alt: Build Status


.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Code Style: Ruff

CircuitPython BlockDevice for USB mass storage devices


Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython 9.0.0 and later <https://github.com/adafruit/circuitpython>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.


Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/adafruit-circuitpython-usb-host-mass-storage/>`_.
To install for current user:

.. code-block:: shell

    pip3 install adafruit-circuitpython-usb-host-mass-storage

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install adafruit-circuitpython-usb-host-mass-storage

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install adafruit-circuitpython-usb-host-mass-storage

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install adafruit_usb_host_mass_storage

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Usage Example
=============

Print basic information about a device and its first (and usually only) configuration.

.. code-block:: python

    import usb.core
    import os
    import storage
    import time

    from adafruit_usb_host_descriptors import *

    DIR_IN = 0x80

    while True:
        print("searching for devices")
        for device in usb.core.find(find_all=True):
            print("pid", hex(device.idProduct))
            print("vid", hex(device.idVendor))
            print("man", device.manufacturer)
            print("product", device.product)
            print("serial", device.serial_number)
            print("config[0]:")
            config_descriptor = get_configuration_descriptor(device, 0)

            i = 0
            while i < len(config_descriptor):
                descriptor_len = config_descriptor[i]
                descriptor_type = config_descriptor[i + 1]
                if descriptor_type == DESC_CONFIGURATION:
                    config_value = config_descriptor[i + 5]
                    print(f" value {config_value:d}")
                elif descriptor_type == DESC_INTERFACE:
                    interface_number = config_descriptor[i + 2]
                    interface_class = config_descriptor[i + 5]
                    interface_subclass = config_descriptor[i + 6]
                    print(f" interface[{interface_number:d}] class {interface_class:02x} subclass {interface_subclass:02x}")
                elif descriptor_type == DESC_ENDPOINT:
                    endpoint_address = config_descriptor[i + 2]
                    if endpoint_address & DIR_IN:
                        print(f"  IN {endpoint_address:02x}")
                    else:
                        print(f"  OUT {endpoint_address:02x}")
                i += descriptor_len
            print()
        time.sleep(5)

Documentation
=============
API documentation for this library can be found on `Read the Docs <https://docs.circuitpython.org/projects/usb-host-mass-storage/en/latest/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_USB_Host_Mass_Storage/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.

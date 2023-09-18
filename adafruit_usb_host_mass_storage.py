# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_usb_host_mass_storage`
================================================================================

CircuitPython BlockDevice for USB mass storage devices


* Author(s): Scott Shawcroft
"""

import struct
import time
import usb.core
from micropython import const
import adafruit_usb_host_descriptors

try:
    from typing import Optional
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = (
    "https://github.com/adafruit/Adafruit_CircuitPython_USB_Host_Mass_Storage.git"
)

# USB defines
_DIR_OUT = const(0x00)
_DIR_IN = const(0x80)
_REQ_RCPT_INTERFACE = const(1)
_REQ_TYPE_CLASS = const(0x20)

_MP_BLOCKDEV_IOCTL_BLOCK_COUNT = const(4)

_MSC_REQ_GET_GET_MAX_LUN = const(254)

# SCSI commands
_SCSI_CMD_TEST_UNIT_READY = const(0x00)
"""The SCSI Test Unit Ready command is used to determine if a device is ready to transfer data
(read/write), i.e. if a disk has spun up, if a tape is loaded and ready etc. The device does not
perform a self-test operation."""
_SCSI_CMD_INQUIRY = const(0x12)
"""The SCSI Inquiry command is used to obtain basic information from a target device."""
_SCSI_CMD_READ_CAPACITY_10 = const(0x25)
"""The SCSI Read Capacity command is used to obtain data capacity information from a target
device."""
_SCSI_CMD_REQUEST_SENSE = const(0x03)
"""The SCSI Request Sense command is part of the SCSI computer protocol standard. This command is
used to obtain sense data -- status/error information -- from a target device."""
_SCSI_CMD_READ_10 = const(0x28)
"""The READ (10) command requests that the device server read the specified logical block(s) and
transfer them to the data-in buffer."""
_SCSI_CMD_WRITE_10 = const(0x2A)
"""The WRITE (10) command requests that the device server transfer the specified logical block(s)
from the data-out buffer and write them."""


class USBMassStorage:
    """CircuitPython BlockDevice backed by a USB mass storage device (aka thumb drive)."""

    def __init__(self, device: usb.core.Device, lun=0):
        config_descriptor = adafruit_usb_host_descriptors.get_configuration_descriptor(
            device, 0
        )

        self.in_ep = 0
        self.out_ep = 0

        self.sector_count = None
        self.block_size = None
        # Look over each descriptor for mass storage interface and then the two
        # endpoints.
        in_msc_interface = False
        msc_interface = None
        i = 0
        config_value = 0
        while i < len(config_descriptor):
            descriptor_len = config_descriptor[i]
            descriptor_type = config_descriptor[i + 1]
            if descriptor_type == adafruit_usb_host_descriptors.DESC_CONFIGURATION:
                config_value = config_descriptor[i + 5]
            elif descriptor_type == adafruit_usb_host_descriptors.DESC_INTERFACE:
                interface_number = config_descriptor[i + 2]
                interface_class = config_descriptor[i + 5]
                interface_subclass = config_descriptor[i + 6]
                in_msc_interface = interface_class == 8 and interface_subclass == 6
                if in_msc_interface:
                    msc_interface = interface_number
            elif (
                descriptor_type == adafruit_usb_host_descriptors.DESC_ENDPOINT
                and in_msc_interface
            ):
                endpoint_address = config_descriptor[i + 2]
                if endpoint_address & _DIR_IN:
                    self.in_ep = endpoint_address
                else:
                    self.out_ep = endpoint_address
            i += descriptor_len

        if self.in_ep == 0 or self.out_ep == 0:
            raise ValueError("No MSC interface found")

        self.lun = lun
        self.device = device
        self.device.set_configuration(config_value)

        # Get the max lun.
        max_lun = bytearray(1)
        try:
            device.ctrl_transfer(
                _REQ_RCPT_INTERFACE | _REQ_TYPE_CLASS | _DIR_IN,
                _MSC_REQ_GET_GET_MAX_LUN,
                0,
                msc_interface,
                max_lun,
            )
            max_lun = max_lun[0] + 1
        except usb.core.USBError:
            # Stall means 0.
            max_lun = 0

        # SCSI command block
        self.cbw = bytearray(31)
        self.cbw[0:4] = b"\x55\x53\x42\x43"
        self.cbw[14] = self.lun
        # SCSI command status
        self.csw = bytearray(13)
        self.csw[0:4] = b"\x55\x53\x42\x53"

        self._inquire()

        self._wait_for_ready()

    def _scsi_command(self, direction, command, data) -> None:
        """Do a SCSI command over USB. Reads or writes to data depending on direction."""
        struct.pack_into("<IBxB", self.cbw, 8, len(data), direction, len(command))
        self.cbw[15 : 15 + len(command)] = command
        # Write out the command.
        self.device.write(self.out_ep, self.cbw)
        # Depending on the direction, read or write the data.
        if data:
            if direction == _DIR_IN:
                self.device.read(self.in_ep, data)
            else:
                self.device.write(self.out_ep, data)

        # Get the status.
        self.device.read(self.in_ep, self.csw)

    def _wait_for_ready(self, tries=100):
        """Waits for the device to be ready."""
        status = 12
        self.csw[status] = 1
        test_ready = bytearray(6)
        test_ready[0] = _SCSI_CMD_TEST_UNIT_READY
        test_ready[1] = self.lun

        sense_response = bytearray(18)
        sense = bytearray(6)
        sense[0] = _SCSI_CMD_REQUEST_SENSE
        sense[4] = len(sense_response)
        try_num = 0
        self._scsi_command(_DIR_OUT, test_ready, b"")
        while self.csw[status] != 0 and try_num < tries:
            try_num += 1
            time.sleep(0.1)
            self._scsi_command(_DIR_IN, sense, sense_response)
            self._scsi_command(_DIR_OUT, test_ready, b"")

        if self.csw[status] != 0:
            raise RuntimeError("Out of tries")

    def _inquire(self) -> None:
        """Run inquiry command"""
        response = bytearray(36)
        command = bytearray(6)
        command[0] = _SCSI_CMD_INQUIRY
        command[4] = len(response)
        self._scsi_command(_DIR_IN, command, response)

    def _read_capacity(self) -> None:
        """Read the device's capacity and store it in the object"""
        command = bytearray(10)
        command[0] = _SCSI_CMD_READ_CAPACITY_10
        response = bytearray(8)

        self._scsi_command(_DIR_IN, command, response)

        self.sector_count, self.block_size = struct.unpack(">II", response)
        self.sector_count += (
            1  # Response has the last valid number. Count is one greater.
        )

    def readblocks(self, block_num: int, buf: bytearray) -> None:
        """Read data from block_num into buf"""
        command = bytearray(10)
        struct.pack_into(
            ">BBIxH",
            command,
            0,
            _SCSI_CMD_READ_10,
            self.lun,
            block_num,
            len(buf) // 512,
        )

        self._scsi_command(_DIR_IN, command, buf)

    def writeblocks(self, block_num: int, buf: bytearray) -> None:
        """Write data to block_num from buf"""
        command = bytearray(10)
        struct.pack_into(
            ">BBIxH",
            command,
            0,
            _SCSI_CMD_WRITE_10,
            self.lun,
            block_num,
            len(buf) // 512,
        )

        self._scsi_command(_DIR_OUT, command, buf)

    def ioctl(self, operation: int, arg: Optional[int] = None) -> Optional[int]:
        """Perform an IOCTL operation"""
        # This is a standard interface so we need to take arg even though we ignore it.
        # pylint: disable=unused-argument
        if operation == _MP_BLOCKDEV_IOCTL_BLOCK_COUNT:
            if not self.sector_count:
                self._read_capacity()
            return self.sector_count
        return None

# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

""" Test Driver HDF5 """

import unittest

from test import QiskitNatureTestCase
from test.second_q.drivers.test_driver import TestDriver
from qiskit_nature.second_q.drivers import HDF5Driver


class TestDriverHDF5(QiskitNatureTestCase, TestDriver):
    """HDF5 Driver tests."""

    def setUp(self):
        super().setUp()
        driver = HDF5Driver(
            hdf5_input=self.get_resource_path("test_driver_hdf5.hdf5", "second_q/drivers/hdf5d")
        )
        self.driver_result = driver.run()


if __name__ == "__main__":
    unittest.main()

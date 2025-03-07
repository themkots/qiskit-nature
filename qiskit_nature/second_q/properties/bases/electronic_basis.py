# This code is part of Qiskit.
#
# (C) Copyright IBM 2021, 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The definition of the available electronic bases."""

from enum import Enum


class ElectronicBasis(Enum):
    """An enumeration of the available electronic bases.

    This ``Enum`` simply names the available electronic bases. The ``SO`` basis is the *special*
    basis into which an
    :class:`~qiskit_nature.second_q.properties.ElectronicEnergy` must map its
    integrals before being able to perform the mapping to a
    :class:`~qiskit_nature.second_q.operators.SecondQuantizedOp`.
    """

    AO = "atomic"
    MO = "molecular"
    SO = "spin"

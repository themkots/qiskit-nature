# This code is part of Qiskit.
#
# (C) Copyright IBM 2020, 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

""" Test VQE UCC MinimumEigensolver Factory """

import unittest

from test import QiskitNatureTestCase
from qiskit import BasicAer
from qiskit.utils import QuantumInstance

from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD

from qiskit_nature.second_q.mappers import QubitConverter
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.algorithms import VQEUCCFactory
from qiskit_nature.second_q.algorithms.initial_points import HFInitialPoint


class TestVQEUCCFactory(QiskitNatureTestCase):
    """Test VQE UCC MinimumEigensolver Factory"""

    # NOTE: The actual usage of this class is mostly tested in combination with the ground-state
    # eigensolvers (one module above).

    def setUp(self):
        super().setUp()

        self.converter = QubitConverter(JordanWignerMapper())

        self.seed = 50
        self.quantum_instance = QuantumInstance(
            BasicAer.get_backend("statevector_simulator"),
            shots=1,
            seed_simulator=self.seed,
            seed_transpiler=self.seed,
        )
        self.quantum_instance_2 = QuantumInstance(
            BasicAer.get_backend("statevector_simulator"),
            shots=2,
            seed_simulator=self.seed,
            seed_transpiler=self.seed,
        )

        self._vqe_ucc_factory = VQEUCCFactory(quantum_instance=self.quantum_instance)

    def auxiliary_tester(self, title: str, prop: str, cases: tuple):
        """
        Tests the setter and getter of a given property.

        Args:
            title: A string that will be the name of the subTest
            prop: A string making reference to the getter/setter to be tested
            cases: A tuple containing 2 possible instances for that property.
            The first instance needs to be the same used in the constructor.
        """

        with self.subTest(title):
            # Check initialization
            self.assertEqual(getattr(self._vqe_ucc_factory, prop), cases[0])
            self.assertEqual(getattr(self._vqe_ucc_factory.minimum_eigensolver, prop), cases[0])
            # Check factory setter
            setattr(self._vqe_ucc_factory, prop, cases[1])
            self.assertEqual(getattr(self._vqe_ucc_factory, prop), cases[1])
            self.assertEqual(getattr(self._vqe_ucc_factory.minimum_eigensolver, prop), cases[1])
            # Check vqe setter
            setattr(self._vqe_ucc_factory.minimum_eigensolver, prop, cases[0])
            self.assertEqual(getattr(self._vqe_ucc_factory, prop), cases[0])
            self.assertEqual(getattr(self._vqe_ucc_factory.minimum_eigensolver, prop), cases[0])

    def auxiliary_tester_isinstance(self, title: str, prop: str, cases: tuple):
        """
        Tests a getter and setter of a given property.
        Only checks if the type of the property is correct.

        Args:
            title: A string that will be the name of the subTest
            prop: A string making reference to the getter/setter to be tested
            cases: A tuple containing 2 possible types (or classes) for that property.
            The first class (or type) needs to be the same used in the constructor.
        """

        with self.subTest(title):
            # Check initialization
            self.assertTrue(isinstance(getattr(self._vqe_ucc_factory, prop), cases[0]))
            self.assertTrue(
                isinstance(getattr(self._vqe_ucc_factory.minimum_eigensolver, prop), cases[0])
            )
            # Check factory setter
            setattr(self._vqe_ucc_factory, prop, cases[1]())
            self.assertTrue(isinstance(getattr(self._vqe_ucc_factory, prop), cases[1]))
            self.assertTrue(
                isinstance(getattr(self._vqe_ucc_factory.minimum_eigensolver, prop), cases[1])
            )
            # Check vqe setter
            setattr(self._vqe_ucc_factory.minimum_eigensolver, prop, cases[0]())
            self.assertTrue(isinstance(getattr(self._vqe_ucc_factory, prop), cases[0]))
            self.assertTrue(
                isinstance(getattr(self._vqe_ucc_factory.minimum_eigensolver, prop), cases[0])
            )

    def test_setters_getters(self):
        """Test Getter/Setter. These tests are using the getter/setter from the"""

        with self.subTest("Initial Point"):
            self.assertTrue(isinstance(self._vqe_ucc_factory.initial_point, HFInitialPoint))
            initial_point = [1, 2, 3]
            self._vqe_ucc_factory.initial_point = initial_point
            self.assertEqual(self._vqe_ucc_factory.initial_point, initial_point)

        with self.subTest("Ansatz"):
            self.assertEqual(self._vqe_ucc_factory.ansatz, None)
            ansatz = UCCSD()
            self._vqe_ucc_factory.ansatz = ansatz
            self.assertTrue(isinstance(self._vqe_ucc_factory.ansatz, UCCSD))

        with self.subTest("Initial State"):
            self.assertEqual(self._vqe_ucc_factory.initial_state, None)
            initial_state = HartreeFock(4, (1, 1), self.converter)
            self._vqe_ucc_factory.initial_state = initial_state
            self.assertEqual(self._vqe_ucc_factory.initial_state, initial_state)


if __name__ == "__main__":
    unittest.main()

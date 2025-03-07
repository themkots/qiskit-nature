# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Second-order Møller-Plesset perturbation theory (MP2) computation."""

from __future__ import annotations

import numpy as np

from qiskit_nature.exceptions import QiskitNatureError
from qiskit_nature.second_q.circuit.library import UCC
from qiskit_nature.second_q.properties import (
    ParticleNumber,
    ElectronicEnergy,
    GroupedSecondQuantizedProperty,
)
from qiskit_nature.second_q.properties.bases import ElectronicBasis
from qiskit_nature.second_q.properties.integrals import ElectronicIntegrals


from .initial_point import InitialPoint


def _compute_mp2(
    num_occ: int, integral_matrix: np.ndarray, orbital_energies: np.ndarray
) -> tuple[np.ndarray, float]:
    """Compute the T2 amplitudes and MP2 energy correction.

    Args:
        num_occ: The number of occupied molecular orbitals.
        integral_matrix: The two-body molecular orbitals matrix.
        orbital_energies: The orbital energies.

    Returns:
        A tuple consisting of the:
        - T amplitudes t2[i, j, a, b] (i, j in occupied, a, b in virtual).
        - The MP2 energy correction.

    """
    # We use NumPy broadcasting to compute the matrix of occupied - virtual energy deltas with
    # shape (num_occ, num_vir), such that
    # energy_deltas[i, a] = orbital_energy[i] - orbital_energy[a].
    # NOTE In the unrestricted-spin calculation, the orbital energies will be a 2D array, and this
    # logic will need to be revisited.
    energy_deltas = orbital_energies[:num_occ, np.newaxis] - orbital_energies[num_occ:]

    # We now want to compute a 4D tensor of (occupied, occupied) - (virtual, virtual)
    # energy deltas with shape (num_occ, num_vir, num_occ, num_vir), such that
    # double_deltas[i, a, j, b] = orbital_energies[i] + orbital_energies[j]
    #                             - orbital_energies[a] - orbital_energies[b].
    # Again we can use NumPy broadcasting to speed this up.
    double_deltas = energy_deltas[:, :, np.newaxis, np.newaxis] + energy_deltas

    # Create integral matrix that uses occupied and virtual indices rather than MO indices.
    integral_matrix_ovov = integral_matrix[:num_occ, num_occ:, :num_occ, num_occ:]

    # Compute T2 amplitudes and transpose to num_occ, num_occ, num_vir, num_vir.
    t2_amplitudes = (integral_matrix_ovov / double_deltas).transpose(0, 2, 1, 3)

    # Compute MP2 energy correction.
    energy_correction = np.einsum("ijab,iajb", t2_amplitudes, integral_matrix_ovov) * 2
    energy_correction -= np.einsum("ijab,ibja", t2_amplitudes, integral_matrix_ovov)

    return t2_amplitudes, energy_correction


class MP2InitialPoint(InitialPoint):
    """Compute the second-order Møller-Plesset perturbation theory (MP2) initial point.

    The computed MP2 correction coefficients are intended for use as an initial point for the VQE
    parameters in combination with a
    :class:`~qiskit_nature.second_q.circuit.library.ansatzes.ucc.UCC` ansatz.

    The initial point parameters are computed using the :meth:`compute` method, which requires the
    :attr:`grouped_property` and :attr:`ansatz` to be passed as arguments or the
    :attr:`grouped_property` and :attr:`excitation_list` attributes to be set already.

    The :attr:`grouped_property` is required to contain
    :class:`~qiskit_nature.second_q.properties.particle_number.ParticleNumber` and
    :class:`~qiskit_nature.second_q.properties.electronic_energy.ElectronicEnergy`. From
    :class:`~qiskit_nature.second_q.properties.particle_number.ParticleNumber` we obtain the
    ``num_particles`` to infer the number of occupied orbitals.
    :class:`~qiskit_nature.second_q.properties.electronic_energy.ElectronicEnergy` must contain the
    two-body, molecular-orbital ``electronic_integrals`` and the ``orbital_energies``. Optionally,
    the setter will obtain the Hartree-Fock ``reference_energy`` to compute the
    :attr:`total_energy`.

    Setting the :attr:`grouped_property` will compute the :attr:`t2_amplitudes` and
    :attr:`energy_correction`.

    Following computation, one can obtain the initial point array via the :meth:`to_numpy_array`
    method. The initial point parameters that correspond to double excitations in the
    :attr:`excitation_list` will equal the appropriate T2 amplitude, while those below
    :attr:`threshold` or that correspond to single, triple, or higher excitations will be zero.
    """

    def __init__(self, threshold: float = 1e-12) -> None:
        super().__init__()
        self.threshold: float = threshold
        self._ansatz: UCC | None = None
        self._excitation_list: list[tuple[tuple[int, ...], tuple[int, ...]]] | None = None
        self._t2_amplitudes: np.ndarray | None = None
        self._parameters: np.ndarray | None = None
        self._energy_correction: float = 0.0
        self._total_energy: float = 0.0

    @property
    def ansatz(self) -> UCC:
        """The UCC ansatz.

        This is used to ensure that the :attr:`excitation_list` matches with the UCC ansatz that
        will be used with the VQE algorithm.
        """
        return self._ansatz

    @ansatz.setter
    def ansatz(self, ansatz: UCC) -> None:

        # Operators must be built early to compute the excitation list.
        _ = ansatz.operators

        self._invalidate()

        self._excitation_list = ansatz.excitation_list
        self._ansatz = ansatz

    @property
    def excitation_list(self) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        """The list of excitations that the UCC ansatz is using.

        Setting this directly will overwrite any excitation list from the ansatz.
        """
        return self._excitation_list

    @excitation_list.setter
    def excitation_list(self, excitations: list[tuple[tuple[int, ...], tuple[int, ...]]]):
        self._invalidate()

        self._excitation_list = excitations

    @property
    def grouped_property(self) -> GroupedSecondQuantizedProperty | None:
        """The grouped property.

        See
        :class:`~qiskit_nature.second_q.algorithms.initial_points.mp2_initial_point.MP2InitialPoint`
        for information on the required properties.

        Raises:
            QiskitNatureError: If
                :class:`~qiskit_nature.second_q.properties.electronic_energy.ElectronicEnergy` is
                missing or the two-body molecular orbitals matrix or the orbital energies are not
                found.
            QiskitNatureError: If
                :class:`~qiskit_nature.second_q.properties.particle_number.ParticleNumber` is
                missing.
            NotImplementedError: If alpha and beta spin molecular orbitals are not
                identical.
        """
        return self._grouped_property

    @grouped_property.setter
    def grouped_property(self, grouped_property: GroupedSecondQuantizedProperty) -> None:

        electronic_energy: ElectronicEnergy | None = grouped_property.get_property(ElectronicEnergy)
        if electronic_energy is None:
            raise QiskitNatureError(
                "The `ElectronicEnergy` cannot be obtained from the `grouped_property`."
            )

        two_body_mo_integral: ElectronicIntegrals | None = (
            electronic_energy.get_electronic_integral(ElectronicBasis.MO, 2)
        )
        if two_body_mo_integral is None:
            raise QiskitNatureError(
                "The two-body MO `electronic_integrals` cannot be obtained from the `grouped_property`."
            )

        orbital_energies: np.ndarray | None = electronic_energy.orbital_energies
        if orbital_energies is None:
            raise QiskitNatureError(
                "The `orbital_energies` cannot be obtained from the `grouped_property`."
            )

        integral_matrix: np.ndarray = two_body_mo_integral.get_matrix()
        if not np.allclose(integral_matrix, two_body_mo_integral.get_matrix(2)):
            raise NotImplementedError(
                "`MP2InitialPoint` only supports restricted-spin setups. "
                "Alpha and beta spin orbitals must be identical. "
                "See https://github.com/Qiskit/qiskit-nature/issues/645."
            )

        reference_energy = electronic_energy.reference_energy if not None else 0.0

        particle_number: ParticleNumber | None = grouped_property.get_property(ParticleNumber)
        if particle_number is None:
            raise QiskitNatureError(
                "The `ParticleNumber` cannot be obtained from the `grouped_property`."
            )

        # Get number of occupied molecular orbitals as the number of alpha particles.
        # Only valid for restricted-spin setups.
        num_occ = particle_number.num_particles[0]

        self._invalidate()

        t2_amplitudes, energy_correction = _compute_mp2(num_occ, integral_matrix, orbital_energies)

        # Save state.
        self._grouped_property = grouped_property
        self._t2_amplitudes = t2_amplitudes
        self._energy_correction = energy_correction
        self._total_energy = reference_energy + energy_correction

    @property
    def t2_amplitudes(self) -> np.ndarray:
        """T2 amplitudes.

        Given ``t2[i, j, a, b]`` ``i, j`` carry virtual indices, while ``a, b`` carry occupied
        indices.
        """
        return self._t2_amplitudes

    @property
    def energy_correction(self) -> float:
        """The MP2 energy correction."""
        return self._energy_correction

    @property
    def total_energy(self) -> float:
        """The total energy including the Hartree-Fock energy.

        If the reference energy was not obtained from
        :class:`~qiskit_nature.second_q.properties.ElectronicEnergy` this will be equal to
        :attr:`energy_correction`.
        """
        return self._total_energy

    @property
    def threshold(self) -> float:
        """Amplitudes below this vanish in the initial point array."""
        return self._threshold

    @threshold.setter
    def threshold(self, threshold: float) -> None:
        try:
            threshold = abs(float(threshold))
        except TypeError:
            threshold = 0.0

        self._invalidate()

        self._threshold = threshold

    def compute(
        self,
        ansatz: UCC | None = None,
        grouped_property: GroupedSecondQuantizedProperty | None = None,
    ) -> None:
        """Compute the initial point parameter for each excitation.

        See class documentation for more information.

        Args:
            grouped_property: A grouped second-quantized property. See :attr:`grouped_property`.
            ansatz: The UCC ansatz. See :attr:`ansatz`.

        Raises:
            QiskitNatureError: If :attr:`_excitation_list` or :attr:`_grouped_property` is not set.
        """
        if ansatz is not None:
            self.ansatz = ansatz

        if self._excitation_list is None:
            raise QiskitNatureError(
                "The excitation list has not been set directly or via the ansatz. "
                "Not enough information has been provided to compute the initial point. "
                "Set the ansatz or call compute with it as an argument. "
                "The ansatz is not required if the excitation list has been set directly."
            )

        if grouped_property is not None:
            self.grouped_property = grouped_property

        if self._grouped_property is None:
            raise QiskitNatureError("The grouped_property has not been set.")

        self._compute()

    def _compute(self) -> None:
        """Compute the MP2 amplitudes given an excitation list.

        Non-double excitations will have zero coefficient.

        Returns:
            The MP2 T2 amplitudes for each excitation.
        """
        num_occ = self._t2_amplitudes.shape[0]
        amplitudes = np.zeros(len(self.excitation_list))
        for index, excitation in enumerate(self._excitation_list):
            if len(excitation[0]) == 2:
                # Get the amplitude of the double excitation.
                [[i, j], [a, b]] = np.asarray(excitation) % num_occ
                amplitude = self._t2_amplitudes[i, j, a - num_occ, b - num_occ]
                amplitudes[index] = amplitude if abs(amplitude) > self._threshold else 0.0

        self._parameters = amplitudes

    def to_numpy_array(self) -> np.ndarray:
        """The initial point as a NumPy array."""
        if self._parameters is None:
            self.compute()
        return self._parameters

    def _invalidate(self):
        """Invalidate any previous computation."""
        self._parameters = None

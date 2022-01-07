# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An optimization pass that combines adjacent single-qubit rotations."""

from typing import Callable, List, Optional, Sequence, Tuple, cast, TYPE_CHECKING

import numpy as np

from cirq import circuits, ops, protocols
from cirq.optimizers import two_qubit_decompositions

if TYPE_CHECKING:
    import cirq


class MergeInteractions(circuits.PointOptimizer):
    """Combines series of adjacent one and two-qubit gates operating on a pair
    of qubits."""

    def __init__(
        self,
        tolerance: float = 1e-8,
        allow_partial_czs: bool = True,
        post_clean_up: Callable[[Sequence[ops.Operation]], ops.OP_TREE] = lambda op_list: op_list,
    ) -> None:
        super().__init__(post_clean_up=post_clean_up)
        self.tolerance = tolerance
        self.allow_partial_czs = allow_partial_czs

    def optimization_at(
        self, circuit: circuits.Circuit, index: int, op: ops.Operation
    ) -> Optional[circuits.PointOptimizationSummary]:
        if len(op.qubits) != 2:
            return None

        old_operations, indices, matrix = self._scan_two_qubit_ops_into_matrix(
            circuit, index, op.qubits
        )

        old_interaction_count = len(
            [old_op for old_op in old_operations if len(old_op.qubits) == 2]
        )

        switch_to_new = False
        switch_to_new |= any(
            len(old_op.qubits) == 2 and not self._may_keep_old_op(old_op)
            for old_op in old_operations
        )

        # This point cannot be optimized using this method
        if not switch_to_new and old_interaction_count <= 1:
            return None

        # Find a max-3-cz construction.
        new_operations = two_qubit_decompositions.two_qubit_matrix_to_operations(
            op.qubits[0], op.qubits[1], matrix, self.allow_partial_czs, self.tolerance, False
        )
        new_interaction_count = len(
            [new_op for new_op in new_operations if len(new_op.qubits) == 2]
        )

        switch_to_new |= new_interaction_count < old_interaction_count

        if not switch_to_new:
            return None

        return circuits.PointOptimizationSummary(
            clear_span=max(indices) + 1 - index,
            clear_qubits=op.qubits,
            new_operations=new_operations,
        )
    def _may_keep_old_op(self, old_op: 'cirq.Operation') -> bool:
        if self.allow_partial_czs:
            return isinstance(old_op.gate, ops.CZPowGate)
        return isinstance(old_op.gate, ops.CZPowGate) and old_op.gate.exponent == 1

    def _op_to_matrix(
        self, op: ops.Operation, qubits: Tuple['cirq.Qid', ...]
    ) -> Optional[np.ndarray]:
        """Determines the effect of an operation on the given qubits.

        If the operation is a 1-qubit operation on one of the given qubits,
        or a 2-qubit operation on both of the given qubits, and also the
        operation has a known matrix, then a matrix is returned. Otherwise None
        is returned.

        Args:
            op: The operation to understand.
            qubits: The qubits we care about. Order determines matrix tensor
                order.

        Returns:
            None, or else a matrix equivalent to the effect of the operation.
        """
        if any(q not in qubits for q in op.qubits):
            return None

        q1, q2 = qubits

        matrix = protocols.unitary(op, None)
        if matrix is None:
            return None

        assert op is not None
        if op.qubits == qubits:
            return matrix
        if op.qubits == (q2, q1):
            return _flip_kron_order(matrix)
        if op.qubits == (q1,):
            return np.kron(matrix, np.eye(2))
        if op.qubits == (q2,):
            return np.kron(np.eye(2), matrix)

        return None

    def _scan_two_qubit_ops_into_matrix(
        self, circuit: circuits.Circuit, index: Optional[int], qubits: Tuple['cirq.Qid', ...]
    ) -> Tuple[List[ops.Operation], List[int], np.ndarray]:
        """Accumulates operations affecting the given pair of qubits.

        The scan terminates when it hits the end of the circuit, finds an
        operation without a known matrix, or finds an operation that interacts
        the given qubits with other qubits.

        Args:
            circuit: The circuit to scan for operations.
            index: The index to start scanning forward from.
            qubits: The pair of qubits we care about.

        Returns:
            A tuple containing:
                0. The operations.
                1. The moment indices those operations were on.
                2. A matrix equivalent to the effect of the scanned operations.
        """

        product = np.eye(4, dtype=np.complex128)
        all_operations = []
        touched_indices = []

        while index is not None:
            operations = list({circuit.operation_at(q, index) for q in qubits})
            op_data = [self._op_to_matrix(op, qubits) for op in operations if op is not None]

            # Stop at any non-constant or non-local interaction.
            if any(e is None for e in op_data):
                break
            present_ops = [op for op in operations if op]
            present_op_data = cast(List[np.ndarray], op_data)

            for op_mat in present_op_data:
                product = np.dot(op_mat, product)
            all_operations.extend(present_ops)

            touched_indices.append(index)
            index = circuit.next_moment_operating_on(qubits, index + 1)

        return all_operations, touched_indices, product


def _flip_kron_order(mat4x4: np.ndarray) -> np.ndarray:
    """Given M = sum(kron(a_i, b_i)), returns M' = sum(kron(b_i, a_i))."""
    result = np.array([[0] * 4] * 4, dtype=np.complex128)
    order = [0, 2, 1, 3]
    for i in range(4):
        for j in range(4):
            result[order[i], order[j]] = mat4x4[i, j]
    return result

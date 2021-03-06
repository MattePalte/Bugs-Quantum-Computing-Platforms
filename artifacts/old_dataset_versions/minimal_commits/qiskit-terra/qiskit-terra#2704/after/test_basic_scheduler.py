# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test cases for the pulse scheduler passes."""

from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit, schedule
from qiskit.pulse import (Schedule, DriveChannel, AcquireChannel, Acquire,
                          MeasureChannel, MemorySlot)

from qiskit.test.mock import FakeOpenPulse2Q, FakeOpenPulse3Q
from qiskit.test import QiskitTestCase


class TestBasicSchedule(QiskitTestCase):
    """Scheduling tests."""

    def setUp(self):
        self.backend = FakeOpenPulse2Q()
        self.cmd_def = self.backend.defaults().build_cmd_def()

    def test_alap_pass(self):
        """Test ALAP scheduling."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.u2(3.14, 1.57, q[0])
        qc.u2(0.5, 0.25, q[1])
        qc.barrier(q[1])
        qc.u2(0.5, 0.25, q[1])
        qc.barrier(q[0], q[1])
        qc.cx(q[0], q[1])
        qc.measure(q, c)
        sched = schedule(qc, self.backend)
        # X pulse on q0 should end at the start of the CNOT
        expected = Schedule(
            (28, self.cmd_def.get('u2', [0], 3.14, 1.57)),
            self.cmd_def.get('u2', [1], 0.5, 0.25),
            (28, self.cmd_def.get('u2', [1], 0.5, 0.25)),
            (56, self.cmd_def.get('cx', [0, 1])),
            (78, self.cmd_def.get('measure', [0, 1])))
        for actual, expected in zip(sched.instructions, expected.instructions):
            self.assertEqual(actual[0], expected[0])
            self.assertEqual(actual[1].command, expected[1].command)
            self.assertEqual(actual[1].channels, expected[1].channels)

    def test_alap_with_barriers(self):
        """Test that ALAP respects barriers on new qubits."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.u2(0, 0, q[0])
        qc.barrier(q[0], q[1])
        qc.u2(0, 0, q[1])
        sched = schedule(qc, self.backend, method='alap')
        expected = Schedule(
            self.cmd_def.get('u2', [0], 0, 0),
            (28, self.cmd_def.get('u2', [1], 0, 0)))
        for actual, expected in zip(sched.instructions, expected.instructions):
            self.assertEqual(actual[0], expected[0])
            self.assertEqual(actual[1].command, expected[1].command)
            self.assertEqual(actual[1].channels, expected[1].channels)

    def test_alap_aligns_end(self):
        """Test that ALAP always acts as though there is a final global barrier."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.u3(0, 0, 0, q[0])
        qc.u2(0, 0, q[1])
        sched = schedule(qc, self.backend, method='alap')
        expected_sched = Schedule(
            self.cmd_def.get('u2', [1], 0, 0),
            (26, self.cmd_def.get('u3', [0], 0, 0, 0)))
        for actual, expected in zip(sched.instructions, expected_sched.instructions):
            self.assertEqual(actual[0], expected[0])
            self.assertEqual(actual[1].command, expected[1].command)
            self.assertEqual(actual[1].channels, expected[1].channels)
        self.assertEqual(sched.ch_duration(DriveChannel(0)),
                         expected_sched.ch_duration(DriveChannel(1)))

    def test_asap_pass(self):
        """Test ASAP scheduling."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.u2(3.14, 1.57, q[0])
        qc.u2(0.5, 0.25, q[1])
        qc.barrier(q[1])
        qc.u2(0.5, 0.25, q[1])
        qc.barrier(q[0], q[1])
        qc.cx(q[0], q[1])
        qc.measure(q, c)
        sched = schedule(qc, self.backend, method="as_soon_as_possible")
        # X pulse on q0 should start at t=0
        expected = Schedule(
            self.cmd_def.get('u2', [0], 3.14, 1.57),
            self.cmd_def.get('u2', [1], 0.5, 0.25),
            (28, self.cmd_def.get('u2', [1], 0.5, 0.25)),
            (56, self.cmd_def.get('cx', [0, 1])),
            (78, self.cmd_def.get('measure', [0, 1])))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_alap_resource_respecting(self):
        """Test that the ALAP pass properly respects busy resources when backwards scheduling.
        For instance, a CX on 0 and 1 followed by an X on only 1 must respect both qubits'
        timeline."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.cx(q[0], q[1])
        qc.u2(0.5, 0.25, q[1])
        sched = schedule(qc, self.backend, method="as_late_as_possible")
        insts = sched.instructions
        self.assertEqual(insts[0][0], 0)
        self.assertEqual(insts[4][0], 22)

        qc = QuantumCircuit(q, c)
        qc.cx(q[0], q[1])
        qc.u2(0.5, 0.25, q[1])
        qc.measure(q, c)
        sched = schedule(qc, self.backend, method="as_late_as_possible")
        self.assertEqual(sched.instructions[-1][0], 50)

    def test_cmd_def_schedules_unaltered(self):
        """Test that forward scheduling doesn't change relative timing with a command."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.cx(q[0], q[1])
        sched1 = schedule(qc, self.backend, method="as_soon_as_possible")
        sched2 = schedule(qc, self.backend, method="as_late_as_possible")
        self.assertEqual(sched1.instructions, sched2.instructions)
        insts = sched1.instructions
        self.assertEqual(insts[0][0], 0)
        self.assertEqual(insts[1][0], 10)
        self.assertEqual(insts[2][0], 20)
        self.assertEqual(insts[3][0], 20)

    def test_measure_combined(self):
        """
        Test to check for measure on the same qubit which generated another measure schedule.

        The measures on different qubits are combined, but measures on the same qubit
        adds another measure to the schedule.
        """
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.u2(3.14, 1.57, q[0])
        qc.cx(q[0], q[1])
        qc.measure(q[0], c[0])
        qc.measure(q[1], c[1])
        qc.measure(q[1], c[1])
        sched = schedule(qc, self.backend, method="as_soon_as_possible")
        expected = Schedule(
            self.cmd_def.get('u2', [0], 3.14, 1.57),
            (28, self.cmd_def.get('cx', [0, 1])),
            (50, self.cmd_def.get('measure', [0, 1])),
            (60, self.cmd_def.get('measure', [0, 1]).filter(channels=[MeasureChannel(1)])),
            (60, Acquire(duration=10)([AcquireChannel(0), AcquireChannel(1)],
                                      [MemorySlot(0), MemorySlot(1)])))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_3q_schedule(self):
        """Test a schedule that was recommended by David McKay :D """
        backend = FakeOpenPulse3Q()
        cmd_def = backend.defaults().build_cmd_def()
        q = QuantumRegister(3)
        c = ClassicalRegister(3)
        qc = QuantumCircuit(q, c)
        qc.cx(q[0], q[1])
        qc.u2(0.778, 0.122, q[2])
        qc.u3(3.14, 1.57, 0., q[0])
        qc.u2(3.14, 1.57, q[1])
        qc.cx(q[1], q[2])
        qc.u2(0.778, 0.122, q[2])
        sched = schedule(qc, backend)
        expected = Schedule(
            cmd_def.get('cx', [0, 1]),
            (22, cmd_def.get('u2', [1], 3.14, 1.57)),
            (46, cmd_def.get('u2', [2], 0.778, 0.122)),
            (50, cmd_def.get('cx', [1, 2])),
            (72, cmd_def.get('u2', [2], 0.778, 0.122)),
            (74, cmd_def.get('u3', [0], 3.14, 1.57)))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_schedule_multi(self):
        """Test scheduling multiple circuits at once."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc0 = QuantumCircuit(q, c)
        qc0.cx(q[0], q[1])
        qc1 = QuantumCircuit(q, c)
        qc1.cx(q[0], q[1])
        schedules = schedule([qc0, qc1], self.backend)
        expected_insts = schedule(qc0, self.backend).instructions
        self.assertEqual(schedules[0].instructions, expected_insts)

    def test_circuit_name_kept(self):
        """Test that the new schedule gets its name from the circuit."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c, name='CIRCNAME')
        qc.cx(q[0], q[1])
        sched = schedule(qc, self.backend, method="asap")
        self.assertEqual(sched.name, qc.name)
        sched = schedule(qc, self.backend, method="alap")
        self.assertEqual(sched.name, qc.name)

    def test_can_add_gates_into_free_space(self):
        """The scheduler does some time bookkeeping to know when qubits are free to be
        scheduled. Make sure this works for qubits that are used in the future. This was
        a bug, uncovered by this example:

           q0 =  - - - - |X|
           q1 = |X| |u2| |X|

        In ALAP scheduling, the next operation on qubit 0 would be added at t=0 rather
        than immediately before the X gate.
        """
        qr = QuantumRegister(2)
        qc = QuantumCircuit(qr)
        for i in range(2):
            qc.u2(0, 0, [qr[i]])
            qc.u1(3.14, [qr[i]])
            qc.u2(0, 0, [qr[i]])
        sched = schedule(qc, self.backend, method="alap")
        expected = Schedule(
            self.cmd_def.get('u2', [0], 0, 0),
            self.cmd_def.get('u2', [1], 0, 0),
            (28, self.cmd_def.get('u1', [0], 3.14)),
            (28, self.cmd_def.get('u1', [1], 3.14)),
            (28, self.cmd_def.get('u2', [0], 0, 0)),
            (28, self.cmd_def.get('u2', [1], 0, 0)))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_barriers_in_middle(self):
        """As a follow on to `test_can_add_gates_into_free_space`, similar issues
        arose for barriers, specifically.
        """
        qr = QuantumRegister(2)
        qc = QuantumCircuit(qr)
        for i in range(2):
            qc.u2(0, 0, [qr[i]])
            qc.barrier(qr[i])
            qc.u1(3.14, [qr[i]])
            qc.barrier(qr[i])
            qc.u2(0, 0, [qr[i]])
        sched = schedule(qc, self.backend, method="alap")
        expected = Schedule(
            self.cmd_def.get('u2', [0], 0, 0),
            self.cmd_def.get('u2', [1], 0, 0),
            (28, self.cmd_def.get('u1', [0], 3.14)),
            (28, self.cmd_def.get('u1', [1], 3.14)),
            (28, self.cmd_def.get('u2', [0], 0, 0)),
            (28, self.cmd_def.get('u2', [1], 0, 0)))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_only_needed_measures(self):
        """Test that `MeasureChannel`s are only added for measured qubits."""
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.measure(q[1], c[1])
        sched_all_channels = schedule(qc, self.backend, method="as_soon_as_possible").channels
        deleted_channels = [MeasureChannel(0)]
        self.assertNotIn(sched_all_channels, deleted_channels)

    def test_user_mapping_for_memslots(self):
        """
        Test that the new schedule only has required `MeasureChannel`s and that the
        `MemorySlot`s are mapped according to the input circuit.
        """
        q = QuantumRegister(2)
        c = ClassicalRegister(2)
        qc = QuantumCircuit(q, c)
        qc.measure(q[0], c[1])
        sched = schedule(qc, self.backend)
        expected = Schedule(
            self.cmd_def.get('measure', [0, 1]).filter(channels=[MeasureChannel(0)]),
            Acquire(duration=10)([AcquireChannel(0), AcquireChannel(1)],
                                 [MemorySlot(1), MemorySlot(0)]))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_user_mapping_for_memslots_3Q(self):
        """Test measuring two of three qubits."""
        backend = FakeOpenPulse3Q()
        cmd_def = backend.defaults().build_cmd_def()
        q = QuantumRegister(3)
        c = ClassicalRegister(3)
        qc = QuantumCircuit(q, c)
        qc.measure(q[1], c[2])
        qc.measure(q[2], c[0])
        sched = schedule(qc, backend)
        expected = Schedule(
            cmd_def.get('measure', [0, 1, 2]).filter(
                channels=[MeasureChannel(1), MeasureChannel(2)]),
            Acquire(duration=10)([AcquireChannel(0), AcquireChannel(1), AcquireChannel(2)],
                                 [MemorySlot(1), MemorySlot(2), MemorySlot(0)]))
        self.assertEqual(sched.instructions, expected.instructions)

    def test_multiple_measure_in_3Q(self):
        """Test multiple measure, user memslot mapping, 3Q."""
        backend = FakeOpenPulse3Q()
        cmd_def = backend.defaults().build_cmd_def()
        q = QuantumRegister(3)
        c = ClassicalRegister(5)
        qc = QuantumCircuit(q, c)
        qc.measure(q[0], c[2])
        qc.measure(q[0], c[4])
        sched = schedule(qc, backend)
        expected = Schedule(
            cmd_def.get('measure', [0, 1, 2]).filter(channels=[MeasureChannel(0)]),
            Acquire(duration=10)([AcquireChannel(0), AcquireChannel(1), AcquireChannel(2)],
                                 [MemorySlot(2), MemorySlot(0), MemorySlot(1)]),
            (10, cmd_def.get('measure', [0, 1, 2]).filter(channels=[MeasureChannel(0)])),
            (10, Acquire(duration=10)([AcquireChannel(0), AcquireChannel(1), AcquireChannel(2)],
                                      [MemorySlot(4), MemorySlot(0), MemorySlot(1)])))
        self.assertEqual(sched.instructions, expected.instructions)

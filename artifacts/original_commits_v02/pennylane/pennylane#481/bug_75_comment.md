Fixes a bug in the new QubitDevice class, where the function generate_samples() was generating the incorrect samples for a given device probability. In the qubit device they swap the number of qubits measures with the total number of qubits; and also the number_of_states with the num_wires.
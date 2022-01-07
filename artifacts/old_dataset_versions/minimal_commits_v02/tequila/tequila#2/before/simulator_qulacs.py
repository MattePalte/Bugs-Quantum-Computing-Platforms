import qulacs
import numbers, numpy
from tequila import TequilaException
from tequila.utils.bitstrings import BitNumbering, BitString, BitStringLSB
from tequila.wavefunction.qubit_wavefunction import QubitWaveFunction
from tequila.simulators.simulator_base import BackendCircuit, BackendExpectationValue, QCircuit, change_basis
from tequila.utils.keymap import KeyMapRegisterToSubregister
"""
Developer Note:
    Qulacs uses different Rotational Gate conventions: Rx(angle) = exp(i angle/2 X) instead of exp(-i angle/2 X)
    And the same for MultiPauli rotational gates
    The angles are scaled with -1.0 to keep things consistent with the rest of tequila
"""
class TequilaQulacsException(TequilaException):
    def __str__(self):
        return "Error in qulacs backend:" + self.message
class BackendCircuitQulacs(BackendCircuit):
    compiler_arguments = {
        "trotterized": True,
        "swap": False,
        "multitarget": True,
        "controlled_rotation": True, # needed for gates depending on variables
        "gaussian": True,
        "exponential_pauli": False,
        "controlled_exponential_pauli": True,
        "phase": True,
        "power": True,
        "hadamard_power": True,
        "controlled_power": True,
        "controlled_phase": True,
        "toffoli": False,
        "phase_to_z": True,
        "cc_max": False
    }
    numbering = BitNumbering.LSB
    def initialize_state(self, n_qubits = None):
        if n_qubits is None:
            n_qubits = self.n_qubits
        return qulacs.QuantumState(n_qubits)
    def __init__(self, abstract_circuit, noise=None, *args, **kwargs):
        self.op_lookup = {
            'I': qulacs.gate.Identity,
            'X': qulacs.gate.X,
            'Y': qulacs.gate.Y,
            'Z': qulacs.gate.Z,
            'H': qulacs.gate.H,
            'Rx': (lambda c: c.add_parametric_RX_gate, qulacs.gate.RX),
            'Ry': (lambda c: c.add_parametric_RY_gate, qulacs.gate.RY),
            'Rz': (lambda c: c.add_parametric_RZ_gate, qulacs.gate.RZ),
            'SWAP': qulacs.gate.SWAP,
            'Measure': qulacs.gate.Measurement,
            'Exp-Pauli': None
        }
        self.variables = []
        super().__init__(abstract_circuit=abstract_circuit, noise=noise, *args, **kwargs)
        self.has_noise=False
        if noise is not None:
            self.has_noise=True
            self.noise_lookup = {
                'bit flip': [qulacs.gate.BitFlipNoise],
                'phase flip': [lambda target, prob: qulacs.gate.Probabilistic([prob],[qulacs.gate.Z(target)])],
                'phase damp': [lambda target, prob: qulacs.gate.DephasingNoise(target,(1/2)*(1-numpy.sqrt(1-prob)))],
                'amplitude damp': [qulacs.gate.AmplitudeDampingNoise],
                'phase-amplitude damp': [qulacs.gate.AmplitudeDampingNoise,
                                         lambda target, prob: qulacs.gate.DephasingNoise(target,(1/2)*(1-numpy.sqrt(1-prob)))
                                         ],
                'depolarizing': [lambda target,prob: qulacs.gate.DepolarizingNoise(target,3*prob/4)]
            }
            self.circuit=self.add_noise_to_circuit(noise)
    def update_variables(self, variables):
        for k, angle in enumerate(self.variables):
            self.circuit.set_parameter(k, angle(variables))
    def do_simulate(self, variables, initial_state, *args, **kwargs):
        state = self.initialize_state(n_qubits=self.n_qubits)
        lsb = BitStringLSB.from_int(initial_state, nbits=self.n_qubits)
        state.set_computational_basis(BitString.from_binary(lsb.binary).integer)
        self.circuit.update_quantum_state(state)
        wfn = QubitWaveFunction.from_array(arr=state.get_vector(), numbering=self.numbering)
        return wfn
    def convert_measurements(self, backend_result) -> QubitWaveFunction:
        result = QubitWaveFunction()
        # todo there are faster ways
        for k in backend_result:
            converted_key = BitString.from_binary(BitStringLSB.from_int(integer=k, nbits=self.n_qubits).binary)
            if converted_key in result._state:
                result._state[converted_key] += 1
            else:
                result._state[converted_key] = 1
        if hasattr(self, "measurements"):
            mqubits = self.measurements
            keymap = KeyMapRegisterToSubregister(subregister=mqubits, register=[i for i in range(self.n_qubits)])
            result = result.apply_keymap(keymap=keymap)
        return result
    def do_sample(self, samples, circuit, noise_model=None, initial_state=0, *args, **kwargs) -> QubitWaveFunction:
        state = self.initialize_state(self.n_qubits)
        lsb = BitStringLSB.from_int(initial_state, nbits=self.n_qubits)
        state.set_computational_basis(BitString.from_binary(lsb.binary).integer)
        circuit.update_quantum_state(state)
        sampled = state.sampling(samples)
        return self.convert_measurements(backend_result=sampled)
    def fast_return(self, abstract_circuit):
        return False
    def initialize_circuit(self, *args, **kwargs):
        n_qubits = len(self.qubit_map)
        return qulacs.ParametricQuantumCircuit(n_qubits)
    def add_exponential_pauli_gate(self, gate, circuit, variables, *args, **kwargs):
        assert not gate.is_controlled()
        convert = {'x': 1, 'y': 2, 'z': 3}
        pind = [convert[x.lower()] for x in gate.paulistring.values()]
        qind = [self.qubit_map[x] for x in gate.paulistring.keys()]
        if len(gate.extract_variables()) > 0:
            self.variables.append(-gate.parameter * gate.paulistring.coeff)
            circuit.add_parametric_multi_Pauli_rotation_gate(qind, pind,
                                                             -gate.parameter(variables) * gate.paulistring.coeff)
        else:
            circuit.add_multi_Pauli_rotation_gate(qind, pind, -gate.parameter(variables) * gate.paulistring.coeff)
    def add_parametrized_gate(self, gate, circuit, variables, *args, **kwargs):
        op = self.op_lookup[gate.name]
        if gate.name == 'Exp-Pauli':
            self.add_exponential_pauli_gate(gate, circuit, variables)
            return
        else:
            if len(gate.extract_variables()) > 0:
                op = op[0]
                self.variables.append(-gate.parameter)
                op(circuit)(self.qubit_map[gate.target[0]], -gate.parameter(variables=variables))
                if gate.is_controlled():
                    raise TequilaQulacsException("Gates which depend on variables can not be controlled! Gate was:\n{}".format(gate))
                return
            else:
                op = op[1]
                qulacs_gate = op(self.qubit_map[gate.target[0]], -gate.parameter(variables=variables))
        if gate.is_controlled():
            qulacs_gate = qulacs.gate.to_matrix_gate(qulacs_gate)
            for c in gate.control:
                qulacs_gate.add_control_qubit(self.qubit_map[c], 1)
        circuit.add_gate(qulacs_gate)
    def add_basic_gate(self, gate, circuit, *args, **kwargs):
        op = self.op_lookup[gate.name]
        qulacs_gate = op(*[self.qubit_map[t] for t in gate.target])
        if gate.is_controlled():
            qulacs_gate = qulacs.gate.to_matrix_gate(qulacs_gate)
            for c in gate.control:
                qulacs_gate.add_control_qubit(self.qubit_map[c], 1)
        circuit.add_gate(qulacs_gate)

    def add_measurement(self, gate, circuit, *args, **kwargs):
        if hasattr(self, "measurements"):
            raise TequilaQulacsException("Measurement on qubit {} was given twice".format(key))
        else:
            self.measurements = gate.target











    def add_noise_to_circuit(self,noise_model):
        c=self.circuit
        n=noise_model
        g_count=c.get_gate_count()
        new=self.initialize_circuit()
        for i in range(g_count):
            g=c.get_gate(i)
            new.add_gate(g)
            qubits=g.get_target_index_list() + g.get_control_index_list()
            for noise in n.noises:
                if len(qubits) == noise.level:
                    for j,channel in enumerate(self.noise_lookup[noise.name]):
                        for q in qubits:
                            chan=channel(q,noise.probs[j])
                            new.add_gate(chan)
        return new
    def optimize_circuit(self, circuit, max_block_size: int = 4, silent: bool = True, *args, **kwargs):
        """
        Can be overwritten if the backend supports its own circuit optimization
        To be clear: Optimization means optimizing the compiled circuit w.r.t depth not
        optimizing parameters
        :return: Optimized circuit
        """
        old = circuit.calculate_depth()
        opt = qulacs.circuit.QuantumCircuitOptimizer()
        opt.optimize(circuit, max_block_size)
        if not silent:
            print("qulacs: optimized circuit depth from {} to {} with max_block_size {}".format(old,
                                                                                                circuit.calculate_depth(),
                                                                                                max_block_size))
        return circuit
    def sample_all_z_hamiltonian(self, samples, hamiltonian, *args, **kwargs):
        qubits = [q for q in hamiltonian.qubits if q in self.abstract_qubit_map]
        if len(qubits) == 0:
            return sum([ps.coeff for ps in hamiltonian.paulistrings])
        all_qubit_counts = self.do_sample(samples=samples, circuit=self.circuit, *args, **kwargs)
        # compute energy
        E = 0.0
        for paulistring in hamiltonian.paulistrings:
            n_samples = 0
            Etmp = 0.0
            for key, count in all_qubit_counts.items():
                parity = [k for i,k in enumerate(key.array) if i in paulistring._data].count(1)
                sign = (-1) ** parity
                Etmp += sign * count
                n_samples += count
            E += Etmp / samples * paulistring.coeff
        return E
class BackendExpectationValueQulacs(BackendExpectationValue):
    BackendCircuitType = BackendCircuitQulacs
    use_mapping = True
    def simulate(self, variables, *args, **kwargs) -> numpy.array:
        # fast return if possible
        if self.H is None:
            return numpy.asarray([0.0])
        elif len(self.H) == 0:
            return numpy.asarray([0.0])
        elif isinstance(self.H, numbers.Number):
            return numpy.asarray[self.H]
        self.U.update_variables(variables)
        state = self.U.initialize_state()
        self.U.circuit.update_quantum_state(state)
        result = []
        for H in self.H:
            if isinstance(H, numbers.Number):
                result.append(H) # those are accumulated unit strings, e.g 0.1*X(3) in wfn on qubits 0,1
            else:
                result.append(H.get_expectation_value(state))
        return numpy.asarray(result)
    def initialize_hamiltonian(self, hamiltonians):
        result = []
        for H in hamiltonians:
            if self.use_mapping:
                # initialize only the active parts of the Hamiltonian and pre-evaluate the passive ones
                # passive parts are the components of each individual pauli string which act on qubits where the circuit does not act on
                # if the circuit does not act on those qubits the passive parts are always evaluating to 1 (if the pauli operator is Z) or 0 (otherwise)
                # since those qubits are always in state |0>
                non_zero_strings = []
                unit_strings = []
                for ps in H.paulistrings:
                    string = ""
                    for k, v in ps.items():
                        if k in self.U.qubit_map:
                            string += v.upper() + " " + str(self.U.qubit_map[k]) + " "
                        elif v.upper() != "Z":
                            string = "ZERO"
                            break
                    string = string.strip()
                    if string != "ZERO":
                        non_zero_strings.append((ps.coeff, string))
                    elif string == "":
                        unit_strings.append((ps.coeff, string))
                # accumulate unit strings
                if len(unit_strings) > 0:
                    coeffs = [x[0] for x in unit_strings]
                    result.append(sum(coeffs))
                if len(non_zero_strings) > 0:
                    qulacs_H = qulacs.Observable(self.n_qubits)
                    for coeff, string in non_zero_strings:
                        qulacs_H.add_operator(coeff, string)
                    result.append(qulacs_H)
            else:
                if self.U.n_qubits < H.n_qubits:
                    raise TequilaQulacsException(
                        "Hamiltonian has more qubits as the Unitary. Mapped expectationvalues are switched off")
                qulacs_H = qulacs.Observable(self.n_qubits)
                for ps in H.paulistrings:
                    string = ""
                    for k, v in ps.items():
                        string += v.upper() + " " + str(k)
                    qulacs_H.add_operator(ps.coeff, string)
                result.append(qulacs_H)
        return result
    def sample(self, variables, samples, *args, **kwargs) -> numpy.array:
        # todo: generalize in baseclass. Do Hamiltonian mapping on initialization
        self.update_variables(variables)
        state = self.U.initialize_state()
        self.U.circuit.update_quantum_state(state)
        result = []
        for H in self._abstract_hamiltonians:
            E = 0.0
            if H.is_all_z():
                E = self.U.sample_all_z_hamiltonian(samples=samples, hamiltonian=H, *args, **kwargs)
            else:
                for ps in H.paulistrings:
                    # change basis, measurement is destructive so copy the state
                    # to avoid recomputation
                    bc = QCircuit()
                    zero_string = False
                    for idx, p in ps.items():
                        if idx not in self.U.qubit_map:
                            # circuit does not act on the qubit
                            # case1: paulimatrix is 'Z' -> unit factor: ignore that part
                            # case2: zero factor -> continue with next ps
                            if p.upper() != "Z":
                                zero_string = True
                        else:
                            bc += change_basis(target=idx, axis=p)
                    if zero_string:
                        continue
                    qbc = self.U.create_circuit(abstract_circuit=bc, variables=None)
                    Esamples = []
                    for sample in range(samples):
                        if self.U.has_noise:
                            state = self.U.initialize_state()
                            self.U.circuit.update_quantum_state(state)
                            state_tmp = state
                        else:
                            state_tmp = state.copy()
                        if len(bc.gates) > 0:  # otherwise there is no basis change (empty qulacs circuit does not work out)
                            qbc.update_quantum_state(state_tmp)
                        ps_measure = 1.0
                        for idx in ps.keys():
                            if idx not in self.U.qubit_map:
                                continue  # means its 1 or Z and <0|Z|0> = 1 anyway
                            else:
                                M = qulacs.gate.Measurement(self.U.qubit_map[idx], self.U.qubit_map[idx])
                                M.update_quantum_state(state_tmp)
                                measured = state_tmp.get_classical_value(self.U.qubit_map[idx])
                                ps_measure *= (-2.0 * measured + 1.0)  # 0 becomes 1 and 1 becomes -1
                        Esamples.append(ps_measure)
                    E += ps.coeff * sum(Esamples) / len(Esamples)
            result.append(E)
        return numpy.asarray(result)
From bug-reporter: "When measuring on a subset of the qubits, when converting the sampled measurement to register form, the result was widened to all qubits in the call to int2reg. The gives incorrect results in the final register. Instead, we should only widen to the number of measured qubits."
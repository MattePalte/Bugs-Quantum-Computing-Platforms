Fixer: "I've fixed bugs in multi-control-multi-target gate and multi-control-single-target gate of GPU. Before this update, dense matrix gate which satisfy this condition "target_qubit_index_count + control_qubit_index_count > 2^target_qubit_index_count" were not processed correctly since size of index list sent to GPU was wrong. This happens with many controls with small dense matrix gate."
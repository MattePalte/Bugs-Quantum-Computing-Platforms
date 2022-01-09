Reporter: "MergeInteractions checks for isinstance(op, GateOperation) if allowe_partial_czs = False and hence it doesn't behave well with TaggedOperations." Fixer: :"MergeInteractions skips merging CZ gates if there are already equal or fewer in a sequence than the synthesized result (to prevent increasing the gate count). Previously, a tagged partial CZ gate could slip through and not be optimized even if allow_partial_czs=False."
﻿// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

using System;
using Microsoft.Quantum.Simulation.Core;

namespace Microsoft.Quantum.Simulation.QuantumProcessor
{
    public partial class QuantumProcessorDispatcher
    {
        public class QuantumProcessorDispatcherZ : Quantum.Intrinsic.Z
        {
            private QuantumProcessorDispatcher Simulator { get; }

            public QuantumProcessorDispatcherZ(QuantumProcessorDispatcher m) : base(m)
            {
                this.Simulator = m;
            }

            public override Func<Qubit, QVoid> __Body__ => (q1) =>
            {
                Simulator.QuantumProcessor.Z(q1);
                return QVoid.Instance;
            };

            public override Func<(IQArray<Qubit>, Qubit), QVoid> __ControlledBody__ => (_args) =>
            {
                (IQArray<Qubit> ctrls, Qubit q1) = _args;

                if ((ctrls == null) || (ctrls.Count == 0))
                {
                    Simulator.QuantumProcessor.Z(q1);
                }
                else
                {
                    Simulator.QuantumProcessor.ControlledZ(ctrls, q1);
                }

                return QVoid.Instance;
            };
        }
    }
}

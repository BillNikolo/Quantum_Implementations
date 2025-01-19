import netsquid as ns
from netsquid.qubits import qubitapi as qapi
from netsquid.protocols import NodeProtocol

def print_state(qubits, description):
    """Utility function to print quantum states."""
    state = qapi.reduced_dm(qubits)
    print(f"{description}:{state}\n")

class CharlieProtocol(NodeProtocol):
    def __init__(self, node):
        super().__init__(node)

    def run(self):
        print("Charlie's protocol has started.")
        q_A, q_B = qapi.create_qubits(2)  # Create qubits
        qapi.operate(q_A, ns.H)  # Apply Hadamard
        qapi.operate([q_A, q_B], ns.CX)  # Apply CNOT
        print_state([q_A, q_B], "Charlie creates entanglement")

        # Send qubits to Alice and Bob
        self.node.ports["port_q_alice"].tx_output(q_A)
        self.node.ports["port_q_bob"].tx_output(q_B)
        print("Charlie sends qubits to Alice and Bob.")
        print("Charlie's protocol has ended.")



import netsquid as ns
from netsquid.qubits import qubitapi as qapi
from netsquid.protocols import NodeProtocol
from netsquid.components.models.qerrormodels import DepolarNoiseModel

def print_state(qubits, description):
    """Utility function to print quantum states."""
    state = qapi.reduced_dm(qubits)
    print(f"{description}:{state}\n")

class BobProtocol(NodeProtocol):
    def __init__(self, node):
        super().__init__(node)
        #Two different errors for each of the quantum channels
        self.dp_noise_alice = DepolarNoiseModel(depolar_rate=0, time_independent=True)
        self.dp_noise_charlie = DepolarNoiseModel(depolar_rate=0, time_independent=True)

    def run(self):
        print("Bob's protocol has started.")

        # Wait for Charlie's qubit
        yield self.await_port_input(self.node.ports["port_q_charlie"])
        q_bob = self.node.ports["port_q_charlie"].rx_input().items[0]
        self.dp_noise_charlie.error_operation([q_bob ]) 
        print_state([q_bob], "Bob receives qubit from Charlie")

        # Wait for Alice's qubit
        yield self.await_port_input(self.node.ports["port_q_alice"])
        q_alice = self.node.ports["port_q_alice"].rx_input().items[0]
        self.dp_noise_alice.error_operation([q_alice ]) 
        print_state([q_alice], "Bob receives qubit from Alice")

        # Apply decoding operations
        print("Bob starts decoding...")
        qapi.operate([q_bob, q_alice], ns.CX)  # Apply CNOT gate
        print("Bob applies CNOT gate.")
        print_state([q_bob, q_alice], "After CNOT gate")

        qapi.operate(q_bob, ns.H)  # Apply Hadamard gate
        print("Bob applies Hadamard gate.")
        print_state([q_bob, q_alice], "After Hadamard gate")

        # Measure the qubits separately
        print("Preparing to measure qubits separately.")
        m_qA, p_qA = qapi.measure(q_bob)  # Measure q_bob
        m_qB, p_qB = qapi.measure(q_alice)  # Measure q_alice
        print(f"Bob decodes message: {m_qA}{m_qB}")
        print(f"Measurement probabilities: p_qA={p_qA}, p_qB={p_qB}")
        print("Bob's protocol has ended.")

import netsquid as ns
from netsquid.qubits import qubitapi as qapi
from netsquid.protocols import NodeProtocol
from netsquid.nodes import Node, Network
from netsquid.components import QuantumChannel, DepolarNoiseModel
from netsquid.qubits.qubitapi import combine_qubits
from netsquid.components.models.qerrormodels import DepolarNoiseModel



def print_state(qubits, description):
    """Utility function to print quantum states."""
    state = qapi.reduced_dm(qubits)
    print(f"{description}:\n{state}\n")


class AliceProtocol(NodeProtocol):
    def __init__(self, node, operation):
        super().__init__(node)
        self.operation = operation
        self.dp_noise = DepolarNoiseModel(depolar_rate=0, time_independent=True)

    def run(self):
        print("Alice's protocol has started.")
        # Wait for qubit from Charlie
        yield self.await_port_input(self.node.ports["port_q_charlie"])
        q = self.node.ports["port_q_charlie"].rx_input().items[0]  # Retrieve the qubit
        # This one introduce the noise for received qubit. Setting it to True the probabillity counts
        #for each iterration, not time related. Change the rate to see the possible errors to your connection;)
        self.dp_noise.error_operation([q]) 
        print_state([q], "Alice receives qubit")

        # Encode the message
        if self.operation == "00":
            print("Alice applies no operation.")
        elif self.operation == "01":
            qapi.operate(q, ns.X)
            print("Alice applies X gate.")
        elif self.operation == "10":
            qapi.operate(q, ns.Z)
            print("Alice applies Z gate.")
        elif self.operation == "11":
            qapi.operate(q, ns.Z)
            qapi.operate(q, ns.X)
            print("Alice applies Z and X gates.")
        else:
            raise ValueError("Invalid operation.")

        print_state([q], f"Alice encodes message: {self.operation}")
        self.node.ports["port_q_bob"].tx_output(q)  # Send the qubit to Bob
        print("Alice sends the qubit to Bob.")
        print("Alice's protocol has ended.")

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


# Create the network
network = Network("Superdense Coding Network")

# Create nodes
charlie = Node("Charlie", port_names=["port_q_alice", "port_q_bob"])
alice = Node("Alice", port_names=["port_q_charlie", "port_q_bob"])
bob = Node("Bob", port_names=["port_q_charlie", "port_q_alice"])

# Add nodes to the network
network.add_nodes([charlie, alice, bob])

# Add quantum channels
gamma = 0.01
noise_model = DepolarNoiseModel(depolar_rate=gamma)

channel_ca = QuantumChannel("Channel_CA", length=10, models={"quantum_noise": noise_model})
channel_cb = QuantumChannel("Channel_CB", length=10, models={"quantum_noise": noise_model})
channel_ab = QuantumChannel("Channel_AB", length=10, models={"quantum_noise": noise_model})

network.add_connection(charlie, alice, channel_to=channel_ca, port_name_node1="port_q_alice", port_name_node2="port_q_charlie")
network.add_connection(charlie, bob, channel_to=channel_cb, port_name_node1="port_q_bob", port_name_node2="port_q_charlie")
network.add_connection(alice, bob, channel_to=channel_ab, port_name_node1="port_q_bob", port_name_node2="port_q_alice")

# Define the intended message
intended_message = "11"  # Example message to encode

# Assign protocols
charlie_protocol = CharlieProtocol(charlie)
alice_protocol = AliceProtocol(alice, operation=intended_message)
bob_protocol = BobProtocol(bob)

# Start all protocols
charlie_protocol.start()
alice_protocol.start()
bob_protocol.start()

# Run the simulation
print("\n--- Starting the simulation ---")
ns.sim_run()

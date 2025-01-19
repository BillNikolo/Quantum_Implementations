
import netsquid as ns
from netsquid.nodes import Node, Network
from netsquid.components import QuantumChannel, DepolarNoiseModel
from charlie_protocol import CharlieProtocol
from alice_protocol import AliceProtocol
from bob_protocol import BobProtocol

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
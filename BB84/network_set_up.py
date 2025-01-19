
from netsquid.components import QuantumChannel, ClassicalChannel
from netsquid.components.models.qerrormodels import DepolarNoiseModel
from netsquid.nodes import Node, Network
from netsquid.qubits import create_qubits, measure, operate
from netsquid.qubits.operators import H
from textwrap import wrap



def network_setup(rate=0):
    # Create and connect network
    network = Network("BB84Network")

    alice = Node("Alice", port_names=["quantum_out", "classical_in", "classical_out"])
    bob = Node("Bob", port_names=["quantum_in", "classical_in", "classical_out"])

    network.add_nodes([alice, bob])

    # Create a quantum channel with noise
    quantum_channel = QuantumChannel("QuantumChannel",length=1e3)
    classical_channel_to_alice = ClassicalChannel("ClassicalChannelToAlice", length=1e3)
    classical_channel_to_bob = ClassicalChannel("ClassicalChannelToBob", length=1e3)

    network.add_connection(
        alice, bob,
        channel_to=quantum_channel,
        port_name_node1="quantum_out",
        port_name_node2="quantum_in",
        label="quantum_channel_alice_to_bob"
    )
    network.add_connection(
        alice, bob,
        channel_to=classical_channel_to_bob,
        port_name_node1="classical_out",
        port_name_node2="classical_in",
        label="classical_channel_alice_to_bob"
    )
    network.add_connection(
        bob, alice,
        channel_to=classical_channel_to_alice,
        port_name_node1="classical_out",
        port_name_node2="classical_in",
        label="classical_channel_bob_to_alice"
    )
    return alice, bob 
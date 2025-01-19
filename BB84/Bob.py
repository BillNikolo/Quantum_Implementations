import netsquid as ns
from netsquid.protocols import NodeProtocol
from netsquid.components.models.qerrormodels import DepolarNoiseModel
from netsquid.qubits import create_qubits, measure, operate
from netsquid.qubits.operators import H
import random
import time
from textwrap import wrap
import numpy as np
from tools import *


class BobProtocol(NodeProtocol):
    def __init__(self, node, encryption_key_length=32, dp_rate=0):
        super().__init__(node)
        self.num_bits = int(3 * encryption_key_length)
        self.encryption_key_length = encryption_key_length
        self.raw_bits = []
        self.bases = []
        self.sifted_key = []
        self.qber = 0
        self.depolar_noise = DepolarNoiseModel(depolar_rate=dp_rate, time_independent=True)

    def run(self):
        for i in range(self.num_bits):
            port = self.node.ports["quantum_in"]
            basis = random.choice(["Z", "X"])
            self.bases.append(basis)

            yield self.await_port_input(port)
            time.sleep(0)
            qubit = port.rx_input().items[0]
            self.depolar_noise.error_operation([qubit])
            result, _ = measure(qubit, observable=ns.Z if basis == "Z" else ns.X)
            self.raw_bits.append(result)
            print(f"[Bob] Measured qubit {i+1}/{self.num_bits}: Result={result}, Basis={basis}")

            # Send acknowledgment to Alice
            self.node.ports["classical_out"].tx_output(f"ACK_{i + 1}")
            print(f"[Bob] Sent ACK_{i + 1}")

        # Send bases to Alice
        print("[Bob] Sending bases to Alice...")
        yield self.await_port_input(self.node.ports["classical_in"])
        self.node.ports["classical_out"].tx_output(' '.join(self.bases))
        dummy = self.node.ports["classical_in"].rx_input().items[0]

        # Wait for sifted positions from Alice
        yield self.await_port_input(self.node.ports["classical_in"])
        selected_values = self.node.ports["classical_in"].rx_input().items[0]

        # Step 1: Split the final string by the '|' separator
        parts = selected_values.split('|')

        # Step 2: Extract sifted_basis and random_selection
        sifted_basis = list(map(int, parts[0].split()))  # Convert sifted_basis from string to list of integers
        random_selection = list(map(int, parts[1].split()))  # Convert random_selection from string to list of integers

        # Step 3: The last part is the corresponding bits as a single string
        alice_qber_key = parts[2]

        # Print the results
        print("Sifted Basis:", sifted_basis)
        print("Random Selection:", random_selection)
        print("Corresponding Bits:", alice_qber_key)

        # Create the corresponding random key from Bob's measured bits
        bob_qber_key = "".join([f"{self.raw_bits[item]}" for item in random_selection]) 

        #Check qber
        self.qber = qber_calculation(alice_qber_key, bob_qber_key)
        print(f'Difference: {self.qber} %')

        if self.qber <= 11:
            # Send everything to Bob
            self.encryption_key = encryption_key_generation(sifted_basis, self.raw_bits, self.encryption_key_length)
            self.node.ports["classical_out"].tx_output("OK")
            print("[Bob] Encryption Key: Valid")
        else:
            self.node.ports["classical_out"].tx_output("DISCARD")
            print("[Bob] Encryption Key: Discarded")


    def display_matrix(self):
        # Create a NumPy array for visualization
        matrix = np.array([list(range(1, self.num_bits + 1)), self.bases, self.raw_bits], dtype=object)
        print("\n--- Bob's Measurement Matrix ---")
        print("Bit #   Basis   Bit")
        print(matrix.T)  # Transpose for vertical alignment
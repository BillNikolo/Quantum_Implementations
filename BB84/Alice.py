import netsquid as ns
from netsquid.protocols import NodeProtocol
from netsquid.qubits import create_qubits, measure, operate
from netsquid.qubits.operators import H
import random
from textwrap import wrap
import numpy as np
from tools import *
import math

class AliceProtocol(NodeProtocol):
    def __init__(self, node, encryption_key_length=32):
        super().__init__(node)
        self.num_bits = int(3 * encryption_key_length)
        self.encryption_key_length = encryption_key_length
        self.raw_bits = []
        self.bases = []
        self.sifted_basis = []
        self.encryption_key = {}

    def run(self):
        print("[Alice] Protocol started.")
        for i in range(self.num_bits):
            port = self.node.ports["quantum_out"]
            bit = random.randint(0, 1)
            basis = random.choice(["Z", "X"])
            self.raw_bits.append(bit)
            self.bases.append(basis)

            # Prepare qubit
            qubit = create_qubits(1)[0]
            if basis == "Z":
                if bit == 1:
                    operate(qubit, ns.X)
            elif basis == "X":
                operate(qubit, H)
                if bit == 1:
                    operate(qubit, ns.Z)

            # Transmit qubit
            port.tx_output(qubit)
            print(f"[Alice] Sent qubit {i+1}/{self.num_bits}: Bit={bit}, Basis={basis}")

            # Wait for acknowledgment
            yield self.await_port_input(self.node.ports["classical_in"])
            ack = self.node.ports["classical_in"].rx_input().items[0]
            if ack != f"ACK_{i + 1}":
                print(f"[Alice] Error: Expected ACK_{i}, got {ack}")
                return

        # Wait for Bob's bases
        print("[Alice] Waiting for Bob's bases...")
        self.node.ports["classical_out"].tx_output("None")
        yield self.await_port_input(self.node.ports["classical_in"])
        bob_bases = (self.node.ports["classical_in"].rx_input().items[0]).split()
        print("[Alice] Received Bob's bases:", bob_bases)

        # Find sifted positions (where bases match)
        self.sifted_basis = [i for i, (a_basis, b_basis) in enumerate(zip(self.bases, bob_bases)) if a_basis == b_basis]
        print("[Alice] Initial sifted positions:", self.sifted_basis)

        # Calculate 20% of the list length
        eleven_percent_count = math.ceil(len(self.sifted_basis) * 0.20)

        # Randomly select 20% of the numbers
        random_selection = random.sample(self.sifted_basis, eleven_percent_count)

        print(random_selection, type(random_selection))

        # Remove the selected positions from self.sifted_basis
        self.sifted_basis = [item for item in self.sifted_basis if item not in random_selection]

        # Initialize an empty list to store the concatenated strings
        concatenated_strings = []

        # Loop through the random_selection to get the corresponding indexes and bits
        for selected_item in random_selection:
            corresponding_bit = self.raw_bits[selected_item]  # Get the corresponding bit

            # Create the concatenated string with sifted_basis item, random_selection item, and corresponding raw_bits
            concatenated_strings.append(f"{corresponding_bit}")
            
        # Now concatenate the remaining sifted_basis, random_selection, and corresponding bits into one string
        selected_values = " ".join([f"{item}" for item in self.sifted_basis])  
        selected_values += "|"  
        selected_values += " ".join([f"{item}" for item in random_selection]) 
        selected_values += "|"  
        selected_values += "".join(concatenated_strings)  

        print("[Alice] Final sifted basis, Random Selection and Corresponding Bits:", selected_values)

        # Send everything to Bob
        self.node.ports["classical_out"].tx_output(''.join(selected_values))
        print("[Alice] Selected values sent to Bob.")
        yield self.await_port_input(self.node.ports["classical_in"])
        bobs_answer = self.node.ports["classical_in"].rx_input().items[0]
        
        if bobs_answer == "OK":
            self.encryption_key = encryption_key_generation(self.sifted_basis, self.raw_bits, self.encryption_key_length)
            print("[Alice] Secure communication of the Encryption Key: Successful")
        else:
            print("[Alice] Secure communication of the Encryption Key: Unsuccessful")
            print("[Alice] Key discarded")

    def display_matrix(self):
        # Create a NumPy array for visualization
        matrix = np.array([list(range(1, self.num_bits + 1)), self.bases, self.raw_bits], dtype=object)
        print("\n--- Alice's Measurement Matrix ---")
        print("Bit #   Basis   Bit")
        print(matrix.T)  # Transpose for vertical alignment
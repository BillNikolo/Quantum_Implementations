import netsquid as ns
from netsquid.components import QuantumChannel, ClassicalChannel
from netsquid.components.models.qerrormodels import DepolarNoiseModel
from netsquid.nodes import Node, Network
from netsquid.protocols import NodeProtocol
from netsquid.qubits import create_qubits, measure, operate
from netsquid.qubits.operators import H
import random
import time
from textwrap import wrap
import numpy as np
import math
from tqdm import tqdm
import matplotlib.pyplot as plt


class AliceProtocol(NodeProtocol):
    def __init__(self, node, encryption_key_length=5):
        super().__init__(node)
        self.num_bits = int(3 * encryption_key_length)
        self.encryption_key_length = encryption_key_length
        self.raw_bits = []
        self.bases = []
        self.sifted_basis = []
        self.encryption_key = {}

    def run(self):
        # print("[Alice] Protocol started.")
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
            # print(f"[Alice] Sent qubit {i+1}/{self.num_bits}: Bit={bit}, Basis={basis}")

            # Wait for acknowledgment
            yield self.await_port_input(self.node.ports["classical_in"])
            ack = self.node.ports["classical_in"].rx_input().items[0]
            if ack != f"ACK_{i + 1}":
                # print(f"[Alice] Error: Expected ACK_{i}, got {ack}")
                return

        # Wait for Bob's bases
        # print("[Alice] Waiting for Bob's bases...")
        self.node.ports["classical_out"].tx_output("None")
        yield self.await_port_input(self.node.ports["classical_in"])
        bob_bases = (self.node.ports["classical_in"].rx_input().items[0]).split()
        # print("[Alice] Received Bob's bases:", bob_bases)

        # Find sifted positions (where bases match)
        self.sifted_basis = [i for i, (a_basis, b_basis) in enumerate(zip(self.bases, bob_bases)) if a_basis == b_basis]
        # print("[Alice] Initial sifted positions:", self.sifted_basis)

        # Calculate 20% of the list length
        eleven_percent_count = math.ceil(len(self.sifted_basis) * 0.20)

        # Randomly select 20% of the numbers
        random_selection = random.sample(self.sifted_basis, eleven_percent_count)

        # print(random_selection, type(random_selection))

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

        # print("[Alice] Final sifted basis, Random Selection and Corresponding Bits:", selected_values)

        # Send everything to Bob
        self.node.ports["classical_out"].tx_output(''.join(selected_values))
        # print("[Alice] Selected values sent to Bob.")
        yield self.await_port_input(self.node.ports["classical_in"])
        bobs_answer = self.node.ports["classical_in"].rx_input().items[0]
        
        if bobs_answer == "OK":
            self.encryption_key = encryption_key_generation(self.sifted_basis, self.raw_bits, self.encryption_key_length)
            # print("[Alice] Secure communication of the Encryption Key: Successful")
            return 1
        else:
            pass
            # print("[Alice] Secure communication of the Encryption Key: Unsuccessful")
            # print("[Alice] Key discarded")

    def display_matrix(self):
        # Create a NumPy array for visualization
        matrix = np.array([list(range(1, self.num_bits + 1)), self.bases, self.raw_bits], dtype=object)
        # print("\n--- Alice's Measurement Matrix ---")
        # print("Bit #   Basis   Bit")
        # print(matrix.T)  # Transpose for vertical alignment

class BobProtocol(NodeProtocol):
    def __init__(self, node, encryption_key_length,dp_rate=0):
        super().__init__(node)
        self.num_bits = int(3 * encryption_key_length)
        self.encryption_key_length = encryption_key_length
        self.raw_bits = []
        self.bases = []
        self.sifted_key = []
        self.qber = 0
        self.depolar_noise = DepolarNoiseModel(depolar_rate=dp_rate, time_independent=True)

    def run(self):

        time.sleep(0)
        for i in range(self.num_bits):
            port = self.node.ports["quantum_in"]
            basis = random.choice(["Z", "X"])
            self.bases.append(basis)

            yield self.await_port_input(port)
            qubit = port.rx_input().items[0]
            self.depolar_noise.error_operation([qubit])
            result, _ = measure(qubit, observable=ns.Z if basis == "Z" else ns.X)
            self.raw_bits.append(result)
            # print(f"[Bob] Measured qubit {i+1}/{self.num_bits}: Result={result}, Basis={basis}")

            # Send acknowledgment to Alice
            self.node.ports["classical_out"].tx_output(f"ACK_{i + 1}")
            # print(f"[Bob] Sent ACK_{i + 1}")

        # Send bases to Alice
        # print("[Bob] Sending bases to Alice...")
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
        # print("Sifted Basis:", sifted_basis)
        # print("Random Selection:", random_selection)
        # print("Corresponding Bits:", alice_qber_key)

        # Create the corresponding random key from Bob's measured bits
        bob_qber_key = "".join([f"{self.raw_bits[item]}" for item in random_selection]) 

        #Check qber
        self.qber = qber_calculation(alice_qber_key, bob_qber_key)
        # print(f'Difference: {self.qber} %')

        if self.qber < 11.1:
            # Send everything to Bob
            self.encryption_key = encryption_key_generation(sifted_basis, self.raw_bits, self.encryption_key_length)
            self.node.ports["classical_out"].tx_output("OK")
            # print("[Bob] Encryption Key: Valid")
        else:
            self.node.ports["classical_out"].tx_output("DISCARD")
            # print("[Bob] Encryption Key: Discarded")


    def display_matrix(self):
        # Create a NumPy array for visualization
        matrix = np.array([list(range(1, self.num_bits + 1)), self.bases, self.raw_bits], dtype=object)
        # print("\n--- Bob's Measurement Matrix ---")
        # print("Bit #   Basis   Bit")
        # print(matrix.T)  # Transpose for vertical alignment

def network_setup(rate=0):
    # Create and connect network
    network = Network("BB84Network")

    alice = Node("Alice", port_names=["quantum_out", "classical_in", "classical_out"])
    bob = Node("Bob", port_names=["quantum_in", "classical_in", "classical_out"])

    network.add_nodes([alice, bob])

    # # Create a depolarizing noise model
    # depolar_noise = DepolarNoiseModel(depolar_rate=rate)
    # Create a quantum channel with noise
    quantum_channel = QuantumChannel(
        "QuantumChannel",
        length=1e3,
    )

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

def qber_calculation(str1, str2):
    # Ensure both strings are of the same length
    if len(str1) != len(str2):
        raise ValueError("The input strings must have the same length.")

    # Initialize a counter for differing positions
    differing_count = 0

    # Loop through each digit and compare the two strings
    for digit1, digit2 in zip(str1, str2):
        if digit1 != digit2:
            differing_count += 1

    # Calculate the percentage of differing digits
    percentage_differing = (differing_count / len(str1)) * 100

    return percentage_differing

def encryption_key_generation(sifted_basis, raw_bits, length):
    encryption_key = ""
    # Loop through the sifted_basis to get the corresponding indexes and bits
    for selected_item in sifted_basis[:length]:
        encryption_key += str(raw_bits[selected_item])  # Get the corresponding bit
    
    return encryption_key


if __name__ == '__main__':

    # key_list = [32, 64, 128, 256, 512, 1024, 2048]
    key_list = [32,]
    for key_length in key_list:

        #Set the number of samples per gamma change
        number_of_samples_per_gamma = 200
        average_gamma_list = []

        for i in tqdm(range(0, 101), desc="Processing Gamma Changes"):
            average_gamma = 0
            for j in range(number_of_samples_per_gamma):
                # Run protocols
                alice, bob = network_setup()
                alice_protocol = AliceProtocol(alice, key_length)
                bob_protocol = BobProtocol(bob, key_length, dp_rate=i/100)

                alice_protocol.start()
                bob_protocol.start()

                ns.sim_run()

                average_gamma += bob_protocol.qber

                # print("\n--- Matrix Summary ---")
                # alice_protocol.display_matrix()
                # bob_protocol.display_matrix()

                # print(f"Alice's Encryption Key: {alice_protocol.encryption_key}")
                # print(f"Bob's Encryption Key: {bob_protocol.encryption_key}")
            
            average_gamma_list.append(average_gamma/number_of_samples_per_gamma)

        
        gamma_values = [i / 100 for i in range(len(average_gamma_list))]
        # Plot QBER vs Gamma with threshold line and shaded area to the right
        plt.figure(figsize=(8, 6))
        plt.plot(gamma_values, average_gamma_list, label="QBER", marker='o', linestyle='-')

        # Add labels, title, and legend
        plt.title("QBER vs Gamma")
        plt.xlabel("Gamma (0 - 1)")
        plt.ylabel("QBER (%)")
        plt.grid(True)
        plt.legend()

        # Save the plot
        plt.savefig(f'/home/baffledbilly/Desktop/Quantum Project/QBER_vs_Gamma_(N={number_of_samples_per_gamma}, K={key_length})_test.png')
        
        print(average_gamma_list)

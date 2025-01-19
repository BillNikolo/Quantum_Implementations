
import netsquid as ns
from netsquid.qubits import qubitapi as qapi
from netsquid.protocols import NodeProtocol
from netsquid.components.models.qerrormodels import DepolarNoiseModel

def print_state(qubits, description):
    """Utility function to print quantum states."""
    state = qapi.reduced_dm(qubits)
    print(f"{description}:{state}\n")

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

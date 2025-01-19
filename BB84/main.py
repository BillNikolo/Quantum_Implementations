import netsquid as ns
from netsquid.qubits import create_qubits, measure, operate
from netsquid.qubits.operators import H
from textwrap import wrap
from Alice import *
from Bob import *
from network_set_up import *

if __name__ == '__main__':
    # Run protocols
    alice, bob = network_setup()
    key_length = 64
    alice_protocol = AliceProtocol(alice, key_length)
    bob_protocol = BobProtocol(bob, key_length, dp_rate=0)

    alice_protocol.start()
    bob_protocol.start()

    ns.sim_run()

    print("\n--- Matrix Summary ---")
    alice_protocol.display_matrix()
    bob_protocol.display_matrix()
    print("\n--- Sifted Key ---")
    print(f"Alice's Encryption Key: {alice_protocol.encryption_key}")
    print(f"Bob's Encryption Key: {bob_protocol.encryption_key}")
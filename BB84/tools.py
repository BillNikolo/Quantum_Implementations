
def encryption_key_generation(sifted_basis, raw_bits, length):
    encryption_key = ""
    # Loop through the sifted_basis to get the corresponding indexes and bits
    for selected_item in sifted_basis[:length]:
        encryption_key += str(raw_bits[selected_item])  # Get the corresponding bit
    
    return encryption_key

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
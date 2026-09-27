"""
ISO 3779 Compliant Vehicle Identification Number (VIN) Generator & Validator.
Per Section 9 of Hackathon guidelines:
- Exactly 17 characters
- Letters I, O, Q are prohibited to avoid confusion with digits 1, 0
- Modulo 11 check digit verification at position 9
"""
import random
import string

# Characters allowed in VINs (excludes I, O, Q)
VIN_CHARS = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"

# Letter to numeric value mapping for VIN check-digit calculation
CHAR_VALUES = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
    'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
}

# Position weight factors for characters 1 through 17
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

# Common World Manufacturer Identifiers (WMI)
WMIS = [
    ("1HG", "Honda USA"),
    ("1FT", "Ford Motor Company USA"),
    ("1GC", "General Motors USA"),
    ("YV1", "Volvo Cars Sweden"),
    ("3C6", "Stellantis / RAM USA"),
    ("5YJ", "Tesla USA"),
    ("WAU", "Audi AG Germany"),
    ("WBA", "BMW Germany"),
]

def calculate_check_digit(vin_17_with_placeholder: str) -> str:
    """Calculates the ISO 3779 9th position check digit for a 17-character string."""
    assert len(vin_17_with_placeholder) == 17
    total = 0
    for i in range(17):
        char = vin_17_with_placeholder[i].upper()
        weight = WEIGHTS[i]
        val = CHAR_VALUES.get(char, 0)
        total += val * weight
    remainder = total % 11
    if remainder == 10:
        return 'X'
    return str(remainder)

def generate_valid_vin(wmi_override: str = None) -> str:
    """Generates a strictly valid 17-character VIN with valid check digit."""
    wmi = wmi_override or random.choice(WMIS)[0]
    # Positions 4-8: Vehicle Descriptor Section (VDS)
    vds = "".join(random.choices(VIN_CHARS, k=5))
    # Position 9: placeholder for check digit
    # Position 10: Model year code (e.g. P=2023, R=2024, S=2025, T=2026)
    year_char = random.choice("PRST")
    # Position 11: Plant code
    plant = random.choice(VIN_CHARS)
    # Positions 12-17: Sequential production number
    seq = "".join(random.choices("0123456789", k=6))
    
    partial = f"{wmi}{vds}_{year_char}{plant}{seq}"
    check_digit = calculate_check_digit(partial)
    return f"{wmi}{vds}{check_digit}{year_char}{plant}{seq}"

def validate_vin(vin: str) -> bool:
    """Validates 17-character VIN against length, illegal characters, and check digit."""
    if not isinstance(vin, str) or len(vin) != 17:
        return False
    vin = vin.upper()
    if any(c in vin for c in "IOQ"):
        return False
    expected = calculate_check_digit(vin[:8] + "_" + vin[9:])
    return vin[8] == expected

if __name__ == "__main__":
    test_vin = generate_valid_vin()
    print(f"Generated VIN: {test_vin}, Valid: {validate_vin(test_vin)}")

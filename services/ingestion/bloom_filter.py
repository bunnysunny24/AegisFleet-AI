"""
Probabilistic Streaming Data Structures for Telemetry Ingestion.
1. Scalable Bloom Filter for O(1) duplicate event detection per Section 9.
2. Sliding Window Sequence Tracker for Out-Of-Order event detection.
"""
import hashlib
import math
from typing import Tuple

class BloomFilter:
    """
    Space-efficient probabilistic data structure for testing whether a (vin, sequence_id)
    telemetry event has already been ingested.
    Guarantees zero false negatives and a configurable false positive probability.
    """
    def __init__(self, expected_elements: int = 1_000_000, false_positive_rate: float = 0.01):
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate

        # Optimal bit array size m = - (n * ln(p)) / (ln(2)^2)
        self.size = int(- (expected_elements * math.log(false_positive_rate)) / (math.log(2) ** 2))
        # Optimal number of hash functions k = (m / n) * ln(2)
        self.num_hashes = max(1, int((self.size / expected_elements) * math.log(2)))
        
        self.bit_array = bytearray(math.ceil(self.size / 8))
        self.count = 0

    def _get_hashes(self, item: str):
        """Generates k hash indices using double hashing (Kirsch-Mitzenmacher optimization)."""
        # Compute two 64-bit hashes from MD5
        digest = hashlib.md5(item.encode("utf-8")).hexdigest()
        h1 = int(digest[:16], 16)
        h2 = int(digest[16:32], 16)

        for i in range(self.num_hashes):
            yield (h1 + i * h2) % self.size

    def add(self, item: str):
        """Adds an item identifier (e.g. 'vin:seq') to the Bloom filter."""
        for bit_index in self._get_hashes(item):
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            self.bit_array[byte_index] |= (1 << bit_offset)
        self.count += 1

    def contains(self, item: str) -> bool:
        """Returns True if the item is probably in the filter, False if definitely not."""
        for bit_index in self._get_hashes(item):
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            if not (self.bit_array[byte_index] & (1 << bit_offset)):
                return False
        return True


class IngestionDeduplicator:
    """
    Combines Bloom filter fast pre-filtering with watermark sequence tracking
    to guarantee idempotency and detect out-of-order vehicle events.
    """
    def __init__(self):
        self.bloom = BloomFilter(expected_elements=500_000, false_positive_rate=0.005)
        # Tracks last observed sequence_id per VIN to identify out-of-order arrivals
        self.vin_watermarks = {}

    def process_event(self, vin: str, seq: int) -> Tuple[bool, bool]:
        """
        Processes (vin, seq).
        Returns: (is_duplicate: bool, is_out_of_order: bool)
        """
        key = f"{vin}:{seq}"
        if self.bloom.contains(key):
            return True, False # Duplicate detected

        # Check out-of-order
        is_ooo = False
        last_seq = self.vin_watermarks.get(vin)
        if last_seq is not None:
            if seq <= last_seq:
                is_ooo = True
            else:
                self.vin_watermarks[vin] = seq
        else:
            self.vin_watermarks[vin] = seq

        # Mark in bloom filter
        self.bloom.add(key)
        return False, is_ooo

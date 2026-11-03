"""Verified original policy stages; not a camera-driven streaming selector.

Four object slots are original fields, not inferred distance bands. All current
stream records have zero in slot 0; original fallback resolves it from slot 1.
"""
SENTINELS = frozenset((0xBE43EDBB, 0x90F70174))


def bind_lod_hashes(slots):
    """Model-handle hashes after 802BDBE0..802BDCE0, ignoring callback effects.

    The original allocates a handle for every new nonzero/nonsentinel hash even
    when the underlying asset has not loaded. Equal hashes share a handle within
    this row. Model availability and eventual distance selection are separate.
    """
    if len(slots) != 4 or any(not isinstance(v, int) or not 0 <= v <= 0xFFFFFFFF
                              for v in slots):
        raise ValueError('Expected four original uint32 model hash slots')
    result = [None if key == 0 or key in SENTINELS else key for key in slots]
    if result[2] is None:
        result[2] = result[1]
    if result[0] is None:
        result[0] = result[1]
    return result


def section_fallback(identifier, available_ids, section_span=10):
    """Original 802B9184 section-ID fallback, not an activation decision.

    Only requests in hundreds 1..20 with positive remainder below the configured
    span are considered. An existing original ID wins. A missing ID may resolve
    to ID+span if that record exists. The span is loaded from world data, not
    necessarily the executable's default value 10.
    """
    if not -32768 <= identifier <= 32767 or not 0 <= section_span <= 0x7FFFFFFF:
        raise ValueError('Unsupported section identifier or span')
    hundred = abs(identifier) // 100 * (-1 if identifier < 0 else 1)
    remainder = identifier - hundred * 100
    if (1 <= hundred <= 20 and 0 < remainder < section_span and
            identifier not in available_ids and identifier + section_span in available_ids):
        return identifier + section_span
    return identifier

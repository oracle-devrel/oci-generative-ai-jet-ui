def biginteger(value):
    """
    Returns a PKCS#11 biginteger bytestream from a Python integer or
    similar type (e.g. :class:`asn1crypto.core.Integer`).

    :param int value: Value
    :rtype: bytes
    """

    value = int(value)  # In case it's a asn1 type or similar

    return value.to_bytes((value.bit_length() + 7) // 8,
                          byteorder='big')

"""
Key handling utilities for Diffie-Hellman keys.
"""

from asn1crypto.algos import DHParameters
from asn1crypto.core import Integer

from . import biginteger
from ..constants import Attribute
from ..exceptions import AttributeTypeInvalid


def decode_dh_domain_parameters(der):
    """
    Decode DER-encoded Diffie-Hellman domain parameters.

    :param bytes der: DER-encoded parameters
    :rtype: dict(Attribute,*)
    """

    params = DHParameters.load(der)

    return {
        Attribute.BASE: biginteger(params['g']),
        Attribute.PRIME: biginteger(params['p']),
    }


def encode_dh_domain_parameters(obj):
    """
    Encode DH domain parameters into DER-encoded format.

    Calculates the subprime if it isn't available.

    :param DomainParameters obj: domain parameters
    :rtype: bytes
    """

    asn1 = DHParameters({
        'g': int.from_bytes(obj[Attribute.BASE], byteorder='big'),
        'p': int.from_bytes(obj[Attribute.PRIME], byteorder='big'),
    })

    return asn1.dump()


def encode_dh_public_key(key):
    """
    Encode DH public key into RFC 3279 DER-encoded format.

    :param PublicKey key: public key
    :rtype: bytes
    """

    asn1 = Integer(int.from_bytes(key[Attribute.VALUE], byteorder='big'))

    return asn1.dump()


def decode_dh_public_key(der):
    """
    Decode a DH public key from RFC 3279 DER-encoded format.

    Returns a `biginteger` encoded as bytes.

    :param bytes der: DER-encoded public key
    :rtype: bytes
    """

    asn1 = Integer.load(der)
    return biginteger(asn1)

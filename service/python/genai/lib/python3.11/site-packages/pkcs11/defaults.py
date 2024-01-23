"""
Default mappings for various key types and mechanisms.

None of this is provided for in PKCS#11 and its correctness should not be
assumed.
"""

from datetime import datetime
from struct import Struct

from .constants import (
    Attribute,
    CertificateType,
    MechanismFlag,
    ObjectClass,
)
from .mechanisms import Mechanism, KeyType, MGF


DEFAULT_GENERATE_MECHANISMS = {
    KeyType.AES: Mechanism.AES_KEY_GEN,
    KeyType.DES2: Mechanism.DES2_KEY_GEN,
    KeyType.DES3: Mechanism.DES3_KEY_GEN,
    KeyType.DH: Mechanism.DH_PKCS_KEY_PAIR_GEN,
    KeyType.DSA: Mechanism.DSA_KEY_PAIR_GEN,
    KeyType.EC: Mechanism.EC_KEY_PAIR_GEN,
    KeyType.RSA: Mechanism.RSA_PKCS_KEY_PAIR_GEN,
    KeyType.X9_42_DH: Mechanism.X9_42_DH_KEY_PAIR_GEN,
    KeyType.EC_EDWARDS: Mechanism.EC_EDWARDS_KEY_PAIR_GEN,
}
"""
Default mechanisms for generating keys.
"""

_ENCRYPTION = MechanismFlag.ENCRYPT | MechanismFlag.DECRYPT
_SIGNING = MechanismFlag.SIGN | MechanismFlag.VERIFY
_WRAPPING = MechanismFlag.WRAP | MechanismFlag.UNWRAP

DEFAULT_KEY_CAPABILITIES = {
    KeyType.AES: _ENCRYPTION | _SIGNING | _WRAPPING,
    KeyType.DES2: _ENCRYPTION | _SIGNING | _WRAPPING,
    KeyType.DES3: _ENCRYPTION | _SIGNING | _WRAPPING,
    KeyType.DH: MechanismFlag.DERIVE,
    KeyType.DSA: _SIGNING,
    KeyType.EC: _SIGNING | MechanismFlag.DERIVE,
    KeyType.RSA: _ENCRYPTION | _SIGNING | _WRAPPING,
    KeyType.GENERIC_SECRET: 0,
    KeyType.EC_EDWARDS: _SIGNING,
}
"""
Default capabilities for generating keys.
"""

DEFAULT_ENCRYPT_MECHANISMS = {
    KeyType.AES: Mechanism.AES_CBC_PAD,
    KeyType.DES2: Mechanism.DES3_CBC_PAD,
    KeyType.DES3: Mechanism.DES3_CBC_PAD,
    KeyType.RSA: Mechanism.RSA_PKCS_OAEP,
}
"""
Default mechanisms for encrypt/decrypt.
"""

DEFAULT_SIGN_MECHANISMS = {
    KeyType.AES: Mechanism.AES_MAC,
    KeyType.DES2: Mechanism.DES3_MAC,
    KeyType.DES3: Mechanism.DES3_MAC,
    KeyType.DSA: Mechanism.DSA_SHA512,
    KeyType.EC: Mechanism.ECDSA_SHA512,
    KeyType.RSA: Mechanism.SHA512_RSA_PKCS,
    KeyType.EC_EDWARDS: Mechanism.EDDSA,
}
"""
Default mechanisms for sign/verify.
"""

DEFAULT_WRAP_MECHANISMS = {
    KeyType.AES: Mechanism.AES_KEY_WRAP,
    KeyType.DES2: Mechanism.DES3_ECB,
    KeyType.DES3: Mechanism.DES3_ECB,
    KeyType.RSA: Mechanism.RSA_PKCS_OAEP,
}
"""
Default mechanism for wrap/unwrap.
"""

DEFAULT_DERIVE_MECHANISMS = {
    KeyType.DH: Mechanism.DH_PKCS_DERIVE,
    KeyType.EC: Mechanism.ECDH1_DERIVE,
    KeyType.X9_42_DH: Mechanism.X9_42_DH_DERIVE,
}
"""
Default mechanisms for key derivation
"""

DEFAULT_PARAM_GENERATE_MECHANISMS = {
    KeyType.DH: Mechanism.DH_PKCS_PARAMETER_GEN,
    KeyType.DSA: Mechanism.DSA_PARAMETER_GEN,
    KeyType.X9_42_DH: Mechanism.X9_42_DH_PARAMETER_GEN,
}
"""
Default mechanisms for domain parameter generation
"""


DEFAULT_MECHANISM_PARAMS = {
    Mechanism.RSA_PKCS_OAEP: (Mechanism.SHA_1, MGF.SHA1, None),
    Mechanism.RSA_PKCS_PSS: (Mechanism.SHA_1, MGF.SHA1, 20),
}
"""
Default mechanism parameters
"""


# (Pack Function, Unpack Function) functions
_bool = (Struct('?').pack, lambda v: Struct('?').unpack(v)[0])
_ulong = (Struct('L').pack, lambda v: Struct('L').unpack(v)[0])
_str = (lambda s: s.encode('utf-8'), lambda b: b.decode('utf-8'))
_date = (lambda s: s.strftime('%Y%m%d').encode('ascii'),
         lambda s: datetime.strptime(s.decode('ascii'), '%Y%m%d').date())
_bytes = (bytes, bytes)
# The PKCS#11 biginteger type is an array of bytes in network byte order.
# If you have an int type, wrap it in biginteger()
_biginteger = _bytes


def _enum(type_):
    """Factory to pack/unpack intos into IntEnums."""
    pack, unpack = _ulong

    return (lambda v: pack(int(v)),
            lambda v: type_(unpack(v)))


ATTRIBUTE_TYPES = {
    Attribute.ALWAYS_AUTHENTICATE: _bool,
    Attribute.ALWAYS_SENSITIVE: _bool,
    Attribute.APPLICATION: _str,
    Attribute.BASE: _biginteger,
    Attribute.CERTIFICATE_TYPE: _enum(CertificateType),
    Attribute.CHECK_VALUE: _bytes,
    Attribute.CLASS: _enum(ObjectClass),
    Attribute.COEFFICIENT: _biginteger,
    Attribute.DECRYPT: _bool,
    Attribute.DERIVE: _bool,
    Attribute.EC_PARAMS: _bytes,
    Attribute.EC_POINT: _bytes,
    Attribute.ENCRYPT: _bool,
    Attribute.END_DATE: _date,
    Attribute.EXPONENT_1: _biginteger,
    Attribute.EXPONENT_2: _biginteger,
    Attribute.EXTRACTABLE: _bool,
    Attribute.HASH_OF_ISSUER_PUBLIC_KEY: _bytes,
    Attribute.HASH_OF_SUBJECT_PUBLIC_KEY: _bytes,
    Attribute.ID: _bytes,
    Attribute.ISSUER: _bytes,
    Attribute.KEY_GEN_MECHANISM: _enum(Mechanism),
    Attribute.KEY_TYPE: _enum(KeyType),
    Attribute.LABEL: _str,
    Attribute.LOCAL: _bool,
    Attribute.MODIFIABLE: _bool,
    Attribute.COPYABLE: _bool,
    Attribute.MODULUS: _biginteger,
    Attribute.MODULUS_BITS: _ulong,
    Attribute.NEVER_EXTRACTABLE: _bool,
    Attribute.OBJECT_ID: _bytes,
    Attribute.PRIME: _biginteger,
    Attribute.PRIME_BITS: _ulong,
    Attribute.PRIME_1: _biginteger,
    Attribute.PRIME_2: _biginteger,
    Attribute.PRIVATE: _bool,
    Attribute.PRIVATE_EXPONENT: _biginteger,
    Attribute.PUBLIC_EXPONENT: _biginteger,
    Attribute.SENSITIVE: _bool,
    Attribute.SERIAL_NUMBER: _bytes,
    Attribute.SIGN: _bool,
    Attribute.SIGN_RECOVER: _bool,
    Attribute.START_DATE: _date,
    Attribute.SUBJECT: _bytes,
    Attribute.SUBPRIME: _biginteger,
    Attribute.SUBPRIME_BITS: _ulong,
    Attribute.TOKEN: _bool,
    Attribute.TRUSTED: _bool,
    Attribute.UNWRAP: _bool,
    Attribute.URL: _str,
    Attribute.VALUE: _biginteger,
    Attribute.VALUE_BITS: _ulong,
    Attribute.VALUE_LEN: _ulong,
    Attribute.VERIFY: _bool,
    Attribute.VERIFY_RECOVER: _bool,
    Attribute.WRAP: _bool,
    Attribute.WRAP_WITH_TRUSTED: _bool,
}
"""
Map of attributes to (serialize, deserialize) functions.
"""

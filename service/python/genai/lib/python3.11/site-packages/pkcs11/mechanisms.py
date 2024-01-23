from enum import IntEnum


class KeyType(IntEnum):
    """
    Key types known by PKCS#11.

    Making use of a given key type requires the appropriate
    :class:`Mechanism` to be available.

    Key types beginning with an underscore are historic and are best avoided.
    """
    RSA = 0x00000000
    """
    See the `RSA section
    <http://docs.oasis-open.org/pkcs11/pkcs11-curr/v2.40/errata01/os/pkcs11-curr-v2.40-errata01-os-complete.html#_Toc441850404>`_
    of the PKCS #11 specification for valid :class:`Mechanism` and
    :class:`pkcs11.constants.Attribute` types.
    """
    DSA = 0x00000001
    """
    See the `DSA section
    <http://docs.oasis-open.org/pkcs11/pkcs11-curr/v2.40/errata01/os/pkcs11-curr-v2.40-errata01-os-complete.html#_Toc441850428>`_
    of the PKCS #11 specification for valid :class:`Mechanism` and
    :class:`pkcs11.constants.Attribute` types.
    """
    DH = 0x00000002
    """
    PKCS #3 Diffie-Hellman key. See the `Diffie-Hellman section
    <http://docs.oasis-open.org/pkcs11/pkcs11-curr/v2.40/errata01/os/pkcs11-curr-v2.40-errata01-os-complete.html#_Toc441850461>`_
    of the PKCS #11 specification for valid :class:`Mechanism` and
    :class:`pkcs11.constants.Attribute` types.
    """
    EC = 0x00000003
    """
    See the `Elliptic Curve section
    <http://docs.oasis-open.org/pkcs11/pkcs11-curr/v2.40/csd01/pkcs11-curr-v2.40-csd01.html#_Toc372721391>`_
    of the PKCS #11 specification for valid :class:`Mechanism` and
    :class:`pkcs11.constants.Attribute` types.
    """
    X9_42_DH = 0x00000004
    """
    X9.42 Diffie-Hellman key.
    """
    _KEA = 0x00000005
    GENERIC_SECRET = 0x00000010
    _RC2 = 0x00000011
    _RC4 = 0x00000012
    _DES = 0x00000013
    DES2 = 0x00000014
    """
    .. warning:: Considered insecure. Use AES where possible.
    """
    DES3 = 0x00000015
    """
    .. warning:: Considered insecure. Use AES where possible.
    """
    _CAST = 0x00000016
    _CAST3 = 0x00000017
    _CAST5 = 0x00000018
    _CAST128 = 0x00000018
    _RC5 = 0x00000019
    _IDEA = 0x0000001A
    _SKIPJACK = 0x0000001B
    _BATON = 0x0000001C
    _JUNIPER = 0x0000001D
    _CDMF = 0x0000001E
    AES = 0x0000001F
    """
    See the `AES section
    <http://docs.oasis-open.org/pkcs11/pkcs11-curr/v2.40/errata01/os/pkcs11-curr-v2.40-errata01-os-complete.html#_Toc441850484>`_
    of PKCS#11 for valid :class:`Mechanism` and
    :class:`pkcs11.constants.Attribute` types.
    """
    BLOWFISH = 0x00000020
    TWOFISH = 0x00000021
    SECURID = 0x00000022
    HOTP = 0x00000023
    ACTI = 0x00000024
    CAMELLIA = 0x00000025
    ARIA = 0x00000026
    _MD5_HMAC = 0x00000027
    SHA_1_HMAC = 0x00000028
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    _RIPEMD128_HMAC = 0x00000029
    _RIPEMD160_HMAC = 0x0000002A
    SHA256_HMAC = 0x0000002B
    SHA384_HMAC = 0x0000002C
    SHA512_HMAC = 0x0000002D
    SHA224_HMAC = 0x0000002E
    SEED = 0x0000002F
    GOSTR3410 = 0x00000030
    GOSTR3411 = 0x00000031
    GOST28147 = 0x00000032

    # from version 3.0
    EC_EDWARDS = 0x00000040

    _VENDOR_DEFINED = 0x80000000

    def __repr__(self):
        return '<KeyType.%s>' % self.name


class Mechanism(IntEnum):
    """
    Cryptographic mechanisms known by PKCS#11.

    The list of supported cryptographic mechanisms for a :class:`pkcs11.Slot`
    can be retrieved with :meth:`pkcs11.Slot.get_mechanisms()`.

    Mechanisms beginning with an underscore are historic and best avoided.
    Descriptions of the `current
    <http://docs.oasis-open.org/pkcs11/pkcs11-curr/v2.40/pkcs11-curr-v2.40.html>`_
    and `historical
    <http://docs.oasis-open.org/pkcs11/pkcs11-hist/v2.40/pkcs11-hist-v2.40.html>`_
    mechanisms, including their valid :class:`pkcs11.constants.Attribute`
    types and `mechanism_param` can be found in the PKCS#11 specification.

    Additionally, while still in the `current` spec, a number of mechanisms
    including cryptographic hash functions and certain block modes are no
    longer considered secure, and should not be used for new applications, e.g.
    MD2, MD5, SHA1, ECB.
    """

    RSA_PKCS_KEY_PAIR_GEN = 0x00000000
    """
    RSA PKCS #1 v1.5 key generation.

    .. note:: Default for generating :attr:`KeyType.RSA` keys.
    """
    RSA_PKCS = 0x00000001
    """
    RSA PKCS #1 v1.5 general purpose mechanism.

    .. warning:: Consider using the more robust PKCS#1 OAEP.
    """
    RSA_PKCS_TPM_1_1 = 0x00004001
    """
    .. warning:: Consider using the more robust PKCS#1 OAEP.
    """
    RSA_PKCS_OAEP = 0x00000009
    """
    RSA PKCS #1 OAEP (v2.0+)

    .. note:: Default for encrypting/decrypting with :attr:`KeyType.RSA` keys.

    Optionally takes a `mechanism_param` which is a tuple of:

    * message digest algorithm used to calculate the digest of the
      encoding parameter (:class:`Mechanism`), default is
      :attr:`Mechanism.SHA_1`;
    * mask generation function to use on the encoded block
      (:class:`MGF`), default is :attr:`MGF.SHA1`;
    * data used as the input for the encoding parameter source
      (:class:`bytes`), default is None.
    """
    RSA_PKCS_OAEP_TPM_1_1 = 0x00004002
    RSA_X_509 = 0x00000003
    """
    X.509 (raw) RSA.

    No padding, supply your own.
    """
    RSA_9796 = 0x00000002
    """
    ISO/IEC 9796 RSA.

    .. warning:: DS1 and DS3 are considered broken. The PKCS #11 spec doesn't
        specify which scheme is used. Use `PSS` instead.
    """

    MD2_RSA_PKCS = 0x00000004
    """
    .. warning:: Not considered secure.
    """
    MD5_RSA_PKCS = 0x00000005
    """
    .. warning:: Not considered secure.
    """
    SHA1_RSA_PKCS = 0x00000006
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    SHA224_RSA_PKCS = 0x00000046
    SHA256_RSA_PKCS = 0x00000040
    SHA384_RSA_PKCS = 0x00000041
    SHA512_RSA_PKCS = 0x00000042
    """
    .. note:: Default for signing/verification with :attr:`KeyType.RSA` keys.
    """

    RSA_PKCS_PSS = 0x0000000D
    """
    RSA PSS without hashing.

    PSS schemes optionally take a tuple of:

    * message digest algorithm used to calculate the digest of the
      encoding parameter (:class:`Mechanism`), default is
      :attr:`Mechanism.SHA_1`;
    * mask generation function to use on the encoded block
      (:class:`MGF`), default is :attr:`MGF.SHA1`; and
    * salt length, default is 20
    """
    SHA1_RSA_PKCS_PSS = 0x0000000E
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    SHA224_RSA_PKCS_PSS = 0x00000047
    SHA256_RSA_PKCS_PSS = 0x00000043
    SHA384_RSA_PKCS_PSS = 0x00000044
    SHA512_RSA_PKCS_PSS = 0x00000045

    RSA_X9_31_KEY_PAIR_GEN = 0x0000000A
    RSA_X9_31 = 0x0000000B
    SHA1_RSA_X9_31 = 0x0000000C
    """
    .. warning:: SHA-1 is no longer considered secure.
    """

    _RIPEMD128_RSA_PKCS = 0x00000007
    _RIPEMD160_RSA_PKCS = 0x00000008

    DSA_KEY_PAIR_GEN = 0x00000010
    """
    .. note:: Default mechanism for generating :attr:`KeyType.DSA` keypairs

    Requires :class:`pkcs11.DomainParameters`.
    """
    DSA = 0x00000011
    """
    DSA without hashing.
    """
    DSA_SHA1 = 0x00000012
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    DSA_SHA224 = 0x00000013
    DSA_SHA256 = 0x00000014
    DSA_SHA384 = 0x00000015
    DSA_SHA512 = 0x00000016
    """
    DSA with SHA512 hashing.

    .. note:: Default for signing/verification with :attr:`KeyType.DSA` keys.
    """

    DH_PKCS_KEY_PAIR_GEN = 0x00000020
    """
    .. note:: Default mechanism for generating :attr:`KeyType.DH` key pairs.

    This is the mechanism defined in PKCS #3.

    Requires :class:`pkcs11.DomainParameters` of
    :attr:`pkcs11.constants.Attribute.BASE` and
    :attr:`pkcs11.constants.Attribute.PRIME`.
    """
    DH_PKCS_DERIVE = 0x00000021
    """
    .. note:: Default mechanism for deriving shared keys from
        :attr:`KeyType.DH` private keys.

    This is the mechanism defined in PKCS #3.

    Takes the other participant's public key
    :attr:`pkcs11.constants.Attribute.VALUE` as the `mechanism_param`.
    """

    X9_42_DH_KEY_PAIR_GEN = 0x00000030
    X9_42_DH_DERIVE = 0x00000031
    X9_42_DH_HYBRID_DERIVE = 0x00000032
    X9_42_MQV_DERIVE = 0x00000033

    _RC2_KEY_GEN = 0x00000100
    _RC2_ECB = 0x00000101
    _RC2_CBC = 0x00000102
    _RC2_MAC = 0x00000103

    _RC2_MAC_GENERAL = 0x00000104
    _RC2_CBC_PAD = 0x00000105

    _RC4_KEY_GEN = 0x00000110
    _RC4 = 0x00000111
    _DES_KEY_GEN = 0x00000120
    _DES_ECB = 0x00000121
    _DES_CBC = 0x00000122
    _DES_MAC = 0x00000123

    _DES_MAC_GENERAL = 0x00000124
    _DES_CBC_PAD = 0x00000125

    DES2_KEY_GEN = 0x00000130
    """
    .. note:: Default for generating DES2 keys.

    .. warning:: Considered insecure. Use AES where possible.
    """
    DES3_KEY_GEN = 0x00000131
    """
    .. note:: Default for generating DES3 keys.

    .. warning:: Considered insecure. Use AES where possible.
    """
    DES3_ECB = 0x00000132
    """
    .. note:: Default for key wrapping with DES2/3.

    .. warning:: Identical blocks will encipher to the same result.
        Considered insecure. Use AES where possible.
    """
    DES3_CBC = 0x00000133
    DES3_MAC = 0x00000134
    """
    .. note:: This is the default for signing/verification with
        :class:`KeyType.DES2` and :class:`KeyType.DES3`.

    .. warning:: Considered insecure. Use AES where possible.
    """

    DES3_MAC_GENERAL = 0x00000135
    DES3_CBC_PAD = 0x00000136
    """
    .. note:: Default for encryption/decryption with DES2/3.

    .. warning:: Considered insecure. Use AES where possible.
    """
    DES3_CMAC_GENERAL = 0x00000137
    DES3_CMAC = 0x00000138

    _CDMF_KEY_GEN = 0x00000140
    _CDMF_ECB = 0x00000141
    _CDMF_CBC = 0x00000142
    _CDMF_MAC = 0x00000143
    _CDMF_MAC_GENERAL = 0x00000144
    _CDMF_CBC_PAD = 0x00000145

    _DES_OFB64 = 0x00000150
    _DES_OFB8 = 0x00000151
    _DES_CFB64 = 0x00000152
    _DES_CFB8 = 0x00000153

    _MD2 = 0x00000200
    _MD2_HMAC = 0x00000201
    _MD2_HMAC_GENERAL = 0x00000202

    _MD5 = 0x00000210
    _MD5_HMAC = 0x00000211
    _MD5_HMAC_GENERAL = 0x00000212

    SHA_1 = 0x00000220
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    SHA_1_HMAC = 0x00000221
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    SHA_1_HMAC_GENERAL = 0x00000222
    """
    .. warning:: SHA-1 is no longer considered secure.
    """

    _RIPEMD128 = 0x00000230
    _RIPEMD128_HMAC = 0x00000231
    _RIPEMD128_HMAC_GENERAL = 0x00000232
    _RIPEMD160 = 0x00000240
    _RIPEMD160_HMAC = 0x00000241
    _RIPEMD160_HMAC_GENERAL = 0x00000242

    SHA256 = 0x00000250
    SHA256_HMAC = 0x00000251
    SHA256_HMAC_GENERAL = 0x00000252

    SHA224 = 0x00000255
    SHA224_HMAC = 0x00000256
    SHA224_HMAC_GENERAL = 0x00000257

    SHA384 = 0x00000260
    SHA384_HMAC = 0x00000261
    SHA384_HMAC_GENERAL = 0x00000262

    SHA512 = 0x00000270
    SHA512_HMAC = 0x00000271
    SHA512_HMAC_GENERAL = 0x00000272

    SECURID_KEY_GEN = 0x00000280
    SECURID = 0x00000282
    HOTP_KEY_GEN = 0x00000290
    HOTP = 0x00000291
    ACTI = 0x000002A0
    ACTI_KEY_GEN = 0x000002A1

    _CAST_KEY_GEN = 0x00000300
    _CAST_ECB = 0x00000301
    _CAST_CBC = 0x00000302
    _CAST_MAC = 0x00000303
    _CAST_MAC_GENERAL = 0x00000304
    _CAST_CBC_PAD = 0x00000305
    _CAST3_KEY_GEN = 0x00000310
    _CAST3_ECB = 0x00000311
    _CAST3_CBC = 0x00000312
    _CAST3_MAC = 0x00000313
    _CAST3_MAC_GENERAL = 0x00000314
    _CAST3_CBC_PAD = 0x00000315

    _CAST5_KEY_GEN = 0x00000320
    _CAST128_KEY_GEN = 0x00000320
    _CAST5_ECB = 0x00000321
    _CAST128_ECB = 0x00000321
    _CAST5_CBC = 0x00000322
    _CAST128_CBC = 0x00000322
    _CAST5_MAC = 0x00000323
    _CAST128_MAC = 0x00000323
    _CAST5_MAC_GENERAL = 0x00000324
    _CAST128_MAC_GENERAL = 0x00000324
    _CAST5_CBC_PAD = 0x00000325
    _CAST128_CBC_PAD = 0x00000325

    _RC5_KEY_GEN = 0x00000330
    _RC5_ECB = 0x00000331
    _RC5_CBC = 0x00000332
    _RC5_MAC = 0x00000333
    _RC5_MAC_GENERAL = 0x00000334
    _RC5_CBC_PAD = 0x00000335

    _IDEA_KEY_GEN = 0x00000340
    _IDEA_ECB = 0x00000341
    _IDEA_CBC = 0x00000342
    _IDEA_MAC = 0x00000343
    _IDEA_MAC_GENERAL = 0x00000344
    _IDEA_CBC_PAD = 0x00000345

    GENERIC_SECRET_KEY_GEN = 0x00000350
    CONCATENATE_BASE_AND_KEY = 0x00000360
    CONCATENATE_BASE_AND_DATA = 0x00000362
    CONCATENATE_DATA_AND_BASE = 0x00000363
    XOR_BASE_AND_DATA = 0x00000364
    EXTRACT_KEY_FROM_KEY = 0x00000365

    SSL3_PRE_MASTER_KEY_GEN = 0x00000370
    SSL3_MASTER_KEY_DERIVE = 0x00000371
    SSL3_KEY_AND_MAC_DERIVE = 0x00000372
    SSL3_MASTER_KEY_DERIVE_DH = 0x00000373
    SSL3_MD5_MAC = 0x00000380
    SSL3_SHA1_MAC = 0x00000381

    TLS_PRE_MASTER_KEY_GEN = 0x00000374
    TLS_MASTER_KEY_DERIVE = 0x00000375
    TLS_KEY_AND_MAC_DERIVE = 0x00000376
    TLS_MASTER_KEY_DERIVE_DH = 0x00000377
    TLS_PRF = 0x00000378

    _MD5_KEY_DERIVATION = 0x00000390
    _MD2_KEY_DERIVATION = 0x00000391
    SHA1_KEY_DERIVATION = 0x00000392

    SHA256_KEY_DERIVATION = 0x00000393
    SHA384_KEY_DERIVATION = 0x00000394
    SHA512_KEY_DERIVATION = 0x00000395
    SHA224_KEY_DERIVATION = 0x00000396

    _PBE_MD2_DES_CBC = 0x000003A0
    _PBE_MD5_DES_CBC = 0x000003A1
    _PBE_MD5_CAST_CBC = 0x000003A2
    _PBE_MD5_CAST3_CBC = 0x000003A3
    _PBE_MD5_CAST5_CBC = 0x000003A4
    _PBE_MD5_CAST128_CBC = 0x000003A4
    _PBE_SHA1_CAST5_CBC = 0x000003A5
    _PBE_SHA1_CAST128_CBC = 0x000003A5
    _PBE_SHA1_RC4_128 = 0x000003A6
    _PBE_SHA1_RC4_40 = 0x000003A7
    _PBE_SHA1_DES3_EDE_CBC = 0x000003A8
    _PBE_SHA1_DES2_EDE_CBC = 0x000003A9
    _PBE_SHA1_RC2_128_CBC = 0x000003AA
    _PBE_SHA1_RC2_40_CBC = 0x000003AB

    PKCS5_PBKD2 = 0x000003B0

    _PBA_SHA1_WITH_SHA1_HMAC = 0x000003C0

    WTLS_PRE_MASTER_KEY_GEN = 0x000003D0
    WTLS_MASTER_KEY_DERIVE = 0x000003D1
    WTLS_MASTER_KEY_DERIVE_DH_ECC = 0x000003D2
    WTLS_PRF = 0x000003D3
    WTLS_SERVER_KEY_AND_MAC_DERIVE = 0x000003D4
    WTLS_CLIENT_KEY_AND_MAC_DERIVE = 0x000003D5

    _KEY_WRAP_LYNKS = 0x00000400
    _KEY_WRAP_SET_OAEP = 0x00000401

    CMS_SIG = 0x00000500

    KIP_DERIVE = 0x00000510
    KIP_WRAP = 0x00000511
    KIP_MAC = 0x00000512

    _CAMELLIA_KEY_GEN = 0x00000550
    _CAMELLIA_ECB = 0x00000551
    _CAMELLIA_CBC = 0x00000552
    _CAMELLIA_MAC = 0x00000553
    _CAMELLIA_MAC_GENERAL = 0x00000554
    _CAMELLIA_CBC_PAD = 0x00000555
    _CAMELLIA_ECB_ENCRYPT_DATA = 0x00000556
    _CAMELLIA_CBC_ENCRYPT_DATA = 0x00000557
    _CAMELLIA_CTR = 0x00000558

    _ARIA_KEY_GEN = 0x00000560
    _ARIA_ECB = 0x00000561
    _ARIA_CBC = 0x00000562
    _ARIA_MAC = 0x00000563
    _ARIA_MAC_GENERAL = 0x00000564
    _ARIA_CBC_PAD = 0x00000565
    _ARIA_ECB_ENCRYPT_DATA = 0x00000566
    _ARIA_CBC_ENCRYPT_DATA = 0x00000567

    SEED_KEY_GEN = 0x00000650
    SEED_ECB = 0x00000651
    """
    .. warning:: Identical blocks will encipher to the same result.
    """
    SEED_CBC = 0x00000652
    SEED_MAC = 0x00000653
    SEED_MAC_GENERAL = 0x00000654
    SEED_CBC_PAD = 0x00000655
    SEED_ECB_ENCRYPT_DATA = 0x00000656
    SEED_CBC_ENCRYPT_DATA = 0x00000657

    _SKIPJACK_KEY_GEN = 0x00001000
    _SKIPJACK_ECB64 = 0x00001001
    _SKIPJACK_CBC64 = 0x00001002
    _SKIPJACK_OFB64 = 0x00001003
    _SKIPJACK_CFB64 = 0x00001004
    _SKIPJACK_CFB32 = 0x00001005
    _SKIPJACK_CFB16 = 0x00001006
    _SKIPJACK_CFB8 = 0x00001007
    _SKIPJACK_WRAP = 0x00001008
    _SKIPJACK_PRIVATE_WRAP = 0x00001009
    _SKIPJACK_RELAYX = 0x0000100a

    _KEA_KEY_PAIR_GEN = 0x00001010
    _KEA_KEY_DERIVE = 0x00001011

    _FORTEZZA_TIMESTAMP = 0x00001020

    _BATON_KEY_GEN = 0x00001030
    _BATON_ECB128 = 0x00001031
    _BATON_ECB96 = 0x00001032
    _BATON_CBC128 = 0x00001033
    _BATON_COUNTER = 0x00001034
    _BATON_SHUFFLE = 0x00001035
    _BATON_WRAP = 0x00001036

    EC_KEY_PAIR_GEN = 0x00001040
    """
    .. note:: Default mechanism for generating :attr:`KeyType.EC` key pairs

    Requires :class:`pkcs11.DomainParameters` of
    :attr:`pkcs11.constants.Attribute.EC_PARAMS`.
    """

    ECDSA = 0x00001041
    """ECDSA with no hashing. Input truncated to 1024-bits."""
    ECDSA_SHA1 = 0x00001042
    """
    .. warning:: SHA-1 is no longer considered secure.
    """
    ECDSA_SHA224 = 0x00001043
    ECDSA_SHA256 = 0x00001044
    ECDSA_SHA384 = 0x00001045
    ECDSA_SHA512 = 0x00001046
    """
    ECDSA with SHA512 hashing.

    .. note:: Default for signing/verification with :attr:`KeyType.EC` keys.
    """

    ECDH1_DERIVE = 0x00001050
    """
    .. note:: Default mechanism for deriving shared keys from
        :attr:`KeyType.EC` private keys.

    Takes a tuple of:

    * key derivation function (:class:`pkcs11.mechanisms.KDF`);
    * shared value (:class:`bytes`); and
    * other participant's :attr:`pkcs11.constants.Attribute.EC_POINT`
      (:class:`bytes`)

    as the `mechanism_param`.
    """
    ECDH1_COFACTOR_DERIVE = 0x00001051
    ECMQV_DERIVE = 0x00001052

    _JUNIPER_KEY_GEN = 0x00001060
    _JUNIPER_ECB128 = 0x00001061
    _JUNIPER_CBC128 = 0x00001062
    _JUNIPER_COUNTER = 0x00001063
    _JUNIPER_SHUFFLE = 0x00001064
    _JUNIPER_WRAP = 0x00001065
    _FASTHASH = 0x00001070

    AES_KEY_GEN = 0x00001080
    """
    .. note:: Default for generating :attr:`KeyType.AES` keys.
    """
    AES_ECB = 0x00001081
    """
    .. note:: Default wrapping mechanism for :attr:`KeyType.AES` keys.

    .. warning:: Identical blocks will encipher to the same result.
    """
    AES_CBC = 0x00001082
    AES_CBC_PAD = 0x00001085
    """
    CBC with PKCS#7 padding to pad files to a whole number of blocks.

    .. note:: Default for encrypting/decrypting with :attr:`KeyType.AES` keys.

    Requires a 128-bit initialisation vector passed as `mechanism_param`.
    """
    AES_CTR = 0x00001086
    AES_CTS = 0x00001089
    AES_MAC = 0x00001083
    """
    .. note:: This is the default for signing/verification with
        :class:`KeyType.AES`.
    """
    AES_MAC_GENERAL = 0x00001084
    AES_CMAC = 0x0000108A
    AES_CMAC_GENERAL = 0x0000108B

    BLOWFISH_KEY_GEN = 0x00001090
    BLOWFISH_CBC = 0x00001091
    BLOWFISH_CBC_PAD = 0x00001094

    TWOFISH_KEY_GEN = 0x00001092
    TWOFISH_CBC = 0x00001093
    TWOFISH_CBC_PAD = 0x00001095

    AES_GCM = 0x00001087
    AES_CCM = 0x00001088
    _AES_KEY_WRAP = 0x00001090
    """This is the old value for AES_KEY_WRAP. Changed in the 2016 spec."""
    _AES_KEY_WRAP_PAD = 0x00001091
    """This is the old value for AES_KEY_WRAP_PAD. Changed in the 2016 spec."""

    AES_XCBC_MAC = 0x0000108C
    AES_XCBC_MAC_96 = 0x0000108D
    AES_GMAC = 0x0000108E

    AES_OFB = 0x00002104
    AES_CFB64 = 0x00002105
    AES_CFB8 = 0x00002106
    AES_CFB128 = 0x00002107

    AES_CFB1 = 0x00002108
    AES_KEY_WRAP = 0x00002109
    AES_KEY_WRAP_PAD = 0x0000210A

    DES_ECB_ENCRYPT_DATA = 0x00001100
    DES_CBC_ENCRYPT_DATA = 0x00001101
    DES3_ECB_ENCRYPT_DATA = 0x00001102
    DES3_CBC_ENCRYPT_DATA = 0x00001103
    AES_ECB_ENCRYPT_DATA = 0x00001104
    AES_CBC_ENCRYPT_DATA = 0x00001105

    GOSTR3410_KEY_PAIR_GEN = 0x00001200
    GOSTR3410 = 0x00001201
    GOSTR3410_WITH_GOSTR3411 = 0x00001202
    GOSTR3410_KEY_WRAP = 0x00001203
    GOSTR3410_DERIVE = 0x00001204
    GOSTR3411 = 0x00001210
    GOSTR3411_HMAC = 0x00001211
    GOST28147_KEY_GEN = 0x00001220
    GOST28147_ECB = 0x00001221
    """
    .. warning:: Identical blocks will encipher to the same result.
    """
    GOST28147 = 0x00001222
    GOST28147_MAC = 0x00001223
    GOST28147_KEY_WRAP = 0x00001224

    DSA_PARAMETER_GEN = 0x00002000
    """
    .. note:: Default mechanism for generating :attr:`KeyType.DSA` domain
        parameters.
    """
    DH_PKCS_PARAMETER_GEN = 0x00002001
    """
    .. note:: Default mechanism for generating :attr:`KeyType.DH` domain
        parameters.

    This is the mechanism defined in PKCS #3.
    """

    X9_42_DH_PARAMETER_GEN = 0x00002002
    """
    .. note:: Default mechanism for generating :attr:`KeyType.X9_42_DH` domain
        parameters (X9.42 DH).
    """

    # from version 3.0
    EDDSA = 0x00001057
    EC_EDWARDS_KEY_PAIR_GEN = 0x00001055

    _VENDOR_DEFINED = 0x80000000

    def __repr__(self):
        return '<Mechanism.%s>' % self.name


class KDF(IntEnum):
    """
    Key Derivation Functions.
    """
    NULL = 0x00000001
    SHA1 = 0x00000002

    SHA1_ASN1 = 0x00000003
    SHA1_CONCATENATE = 0x00000004
    SHA224 = 0x00000005
    SHA256 = 0x00000006
    SHA384 = 0x00000007
    SHA512 = 0x00000008
    CPDIVERSIFY = 0x00000009

    def __repr__(self):
        return '<KDF.%s>' % self.name


class MGF(IntEnum):
    """
    RSA PKCS #1 Mask Generation Functions.
    """
    SHA1 = 0x00000001
    SHA256 = 0x00000002
    SHA384 = 0x00000003
    SHA512 = 0x00000004
    SHA224 = 0x00000005

    def __repr__(self):
        return '<MGF.%s>' % self.name

"""
Certificate handling utilities for X.509 (SSL) certificates.
"""

from asn1crypto.x509 import Certificate

from ..constants import Attribute, ObjectClass, CertificateType
from ..mechanisms import KeyType


def decode_x509_public_key(der):
    """
    Decode a DER-encoded X.509 certificate's public key into a set of
    attributes able to be passed to :meth:`pkcs11.Session.create_object`.

    For PEM-encoded certificates, use :func:`asn1crypto.pem.unarmor`.

    .. warning::

        Does not verify certificate.

    :param bytes der: DER-encoded certificate
    :rtype: dict(Attribute,*)
    """
    x509 = Certificate.load(der)
    key_info = x509.public_key
    key = bytes(key_info['public_key'])

    key_type = {
        'rsa': KeyType.RSA,
        'dsa': KeyType.DSA,
        'ec': KeyType.EC,
    }[key_info.algorithm]

    attrs = {
        Attribute.CLASS: ObjectClass.PUBLIC_KEY,
        Attribute.KEY_TYPE: key_type,
    }

    if key_type is KeyType.RSA:
        from .rsa import decode_rsa_public_key
        attrs.update(decode_rsa_public_key(key))
    elif key_type is KeyType.DSA:
        from .dsa import decode_dsa_domain_parameters, decode_dsa_public_key
        params = key_info['algorithm']['parameters'].dump()

        attrs.update(decode_dsa_domain_parameters(params))
        attrs.update({
            Attribute.VALUE: decode_dsa_public_key(key),
        })
    elif key_type is KeyType.EC:
        params = key_info['algorithm']['parameters'].dump()

        attrs.update({
            Attribute.EC_PARAMS: params,
            Attribute.EC_POINT: key,
        })
    else:
        raise AssertionError("Should not be reached")

    return attrs


def decode_x509_certificate(der, extended_set=False):
    """
    Decode a DER-encoded X.509 certificate into a dictionary of
    attributes able to be passed to :meth:`pkcs11.Session.create_object`.

    Optionally pass `extended_set` to include additional attributes:
    start date, end date and key identifiers.

    For PEM-encoded certificates, use :func:`asn1crypto.pem.unarmor`.

    .. warning::

        Does not verify certificate.

    :param bytes der: DER-encoded certificate
    :param extended_set: decodes more metadata about the certificate
    :rtype: dict(Attribute,*)
    """
    x509 = Certificate.load(der)
    subject = x509.subject
    issuer = x509.issuer
    serial = x509['tbs_certificate']['serial_number']

    template = {
        Attribute.CLASS: ObjectClass.CERTIFICATE,
        Attribute.CERTIFICATE_TYPE: CertificateType.X_509,
        Attribute.SUBJECT: subject.dump(),
        Attribute.ISSUER: issuer.dump(),
        Attribute.SERIAL_NUMBER: serial.dump(),
        Attribute.VALUE: x509.dump(),
    }

    if extended_set:
        start_date = \
            x509['tbs_certificate']['validity']['not_before'].native.date()
        end_date = \
            x509['tbs_certificate']['validity']['not_after'].native.date()

        template.update({
            Attribute.START_DATE: start_date,
            Attribute.END_DATE: end_date,
        })

        # FIXME: is this correct?
        try:
            template[Attribute.HASH_OF_SUBJECT_PUBLIC_KEY] = \
                x509.key_identifier
        except KeyError:
            pass

        try:
            template[Attribute.HASH_OF_ISSUER_PUBLIC_KEY] = \
                x509.authority_key_identifier
        except KeyError:
            pass

    return template

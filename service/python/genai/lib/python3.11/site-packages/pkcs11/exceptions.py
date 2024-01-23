"""
PKCS#11 return codes are exposed as Python exceptions inheriting from
:class:`PKCS11Error`.
"""


class PKCS11Error(RuntimeError):
    """
    Base exception for all PKCS#11 exceptions.
    """


class AlreadyInitialized(PKCS11Error):
    """
    pkcs11 was already initialized with another library.
    """


class AnotherUserAlreadyLoggedIn(PKCS11Error):
    pass


class AttributeTypeInvalid(PKCS11Error):
    pass


class AttributeValueInvalid(PKCS11Error):
    pass


class AttributeReadOnly(PKCS11Error):
    """
    An attempt was made to set a value for an attribute which may not be set by
    the application, or which may not be modified by the application.
    """


class AttributeSensitive(PKCS11Error):
    """
    An attempt was made to obtain the value of an attribute of an object which
    cannot be satisfied because the object is either sensitive or
    un-extractable.
    """


class ArgumentsBad(PKCS11Error):
    """
    Bad arguments were passed into PKCS#11.

    This can indicate missing parameters to a mechanism or some other issue.
    Consult your PKCS#11 vendor documentation.
    """


class DataInvalid(PKCS11Error):
    """
    The plaintext input data to a cryptographic operation is invalid.
    """


class DataLenRange(PKCS11Error):
    """
    The plaintext input data to a cryptographic operation has a bad length.
    Depending on the operation’s mechanism, this could mean that the plaintext
    data is too short, too long, or is not a multiple of some particular block
    size.
    """


class DomainParamsInvalid(PKCS11Error):
    """
    Invalid or unsupported domain parameters were supplied to the function.
    Which representation methods of domain parameters are supported by a given
    mechanism can vary from token to token.
    """


class DeviceError(PKCS11Error):
    pass


class DeviceMemory(PKCS11Error):
    """
    The token does not have sufficient memory to perform the requested
    function.
    """


class DeviceRemoved(PKCS11Error):
    """
    The token was removed from its slot during the execution of the function.
    """


class EncryptedDataInvalid(PKCS11Error):
    """
    The encrypted input to a decryption operation has been determined to be
    invalid ciphertext.
    """


class EncryptedDataLenRange(PKCS11Error):
    """
    The ciphertext input to a decryption operation has been determined to be
    invalid ciphertext solely on the basis of its length.  Depending on the
    operation’s mechanism, this could mean that the ciphertext is too short,
    too long, or is not a multiple of some particular block size.
    """


class ExceededMaxIterations(PKCS11Error):
    """
    An iterative algorithm (for key pair generation, domain parameter
    generation etc.) failed because we have exceeded the maximum number of
    iterations.
    """


class FunctionCancelled(PKCS11Error):
    pass


class FunctionFailed(PKCS11Error):
    pass


class FunctionRejected(PKCS11Error):
    pass


class FunctionNotSupported(PKCS11Error):
    pass


class KeyHandleInvalid(PKCS11Error):
    pass


class KeyIndigestible(PKCS11Error):
    pass


class KeyNeeded(PKCS11Error):
    pass


class KeyNotNeeded(PKCS11Error):
    pass


class KeyNotWrappable(PKCS11Error):
    pass


class KeySizeRange(PKCS11Error):
    pass


class KeyTypeInconsistent(PKCS11Error):
    pass


class KeyUnextractable(PKCS11Error):
    pass


class GeneralError(PKCS11Error):
    """
     In unusual (and extremely unpleasant!) circumstances, a function can fail
     with the return value CKR_GENERAL_ERROR.  When this happens, the token
     and/or host computer may be in an inconsistent state, and the goals of the
     function may have been partially achieved.
     """


class HostMemory(PKCS11Error):
    """
    The computer that the Cryptoki library is running on has insufficient
    memory to perform the requested function.
    """


class MechanismInvalid(PKCS11Error):
    """
    Mechanism can not be used with requested operation.
    """


class MechanismParamInvalid(PKCS11Error):
    pass


class MultipleObjectsReturned(PKCS11Error):
    """
    Multiple objects matched the search parameters.
    """


class MultipleTokensReturned(PKCS11Error):
    """
    Multiple tokens matched the search parameters.
    """


class NoSuchKey(PKCS11Error):
    """
    No key matching the parameters was found.
    """


class NoSuchToken(PKCS11Error):
    """
    No token matching the parameters was found.
    """


class ObjectHandleInvalid(PKCS11Error):
    pass


class OperationActive(PKCS11Error):
    """
    There is already an active operation (or combination of active operations)
    which prevents Cryptoki from activating the specified operation.  For
    example, an active object-searching operation would prevent Cryptoki from
    activating an encryption operation with C_EncryptInit.  Or, an active
    digesting operation and an active encryption operation would prevent
    Cryptoki from activating a signature operation.  Or, on a token which
    doesn’t support simultaneous dual cryptographic operations in a session
    (see the description of the CKF_DUAL_CRYPTO_OPERATIONS flag in the
    CK_TOKEN_INFO structure), an active signature operation would prevent
    Cryptoki from activating an encryption operation.
    """


class OperationNotInitialized(PKCS11Error):
    pass


class PinExpired(PKCS11Error):
    pass


class PinIncorrect(PKCS11Error):
    pass


class PinInvalid(PKCS11Error):
    pass


class PinLenRange(PKCS11Error):
    """The specified PIN is too long or too short."""


class PinLocked(PKCS11Error):
    pass


class PinTooWeak(PKCS11Error):
    pass


class PublicKeyInvalid(PKCS11Error):
    pass


class RandomNoRNG(PKCS11Error):
    pass


class RandomSeedNotSupported(PKCS11Error):
    pass


class SessionClosed(PKCS11Error):
    """
    The session was closed during the execution of the function.
    """


class SessionCount(PKCS11Error):
    """
    An attempt to open a session which does not succeed because there are too
    many existing sessions.
    """


class SessionExists(PKCS11Error):
    pass


class SessionHandleInvalid(PKCS11Error):
    """
    The session handle was invalid. This is usually caused by using an
    old session object that is not known to PKCS#11.
    """


class SessionReadOnly(PKCS11Error):
    """Attempted to write to a read-only session."""


class SessionReadOnlyExists(PKCS11Error):
    pass


class SessionReadWriteSOExists(PKCS11Error):
    """
    If the application calling :meth:`Token.open` already has a R/W SO
    session open with the token, then any attempt to open a R/O session with
    the token fails with this exception.
    """


class SignatureLenRange(PKCS11Error):
    pass


class SignatureInvalid(PKCS11Error):
    pass


class SlotIDInvalid(PKCS11Error):
    pass


class TemplateIncomplete(PKCS11Error):
    """
    Required attributes to create the object were missing.
    """


class TemplateInconsistent(PKCS11Error):
    """
    Template values (including vendor defaults) are contradictory.
    """


class TokenNotPresent(PKCS11Error):
    """
    The token was not present in its slot at the time that the function was
    invoked.
    """


class TokenNotRecognised(PKCS11Error):
    pass


class TokenWriteProtected(PKCS11Error):
    pass


class UnwrappingKeyHandleInvalid(PKCS11Error):
    pass


class UnwrappingKeySizeRange(PKCS11Error):
    pass


class UnwrappingKeyTypeInconsistent(PKCS11Error):
    pass


class UserAlreadyLoggedIn(PKCS11Error):
    pass


class UserNotLoggedIn(PKCS11Error):
    pass


class UserPinNotInitialized(PKCS11Error):
    pass


class UserTooManyTypes(PKCS11Error):
    """
    An attempt was made to have more distinct users simultaneously logged into
    the token than the token and/or library permits.  For example, if some
    application has an open SO session, and another application attempts to log
    the normal user into a session, the attempt may return this error.  It is
    not required to, however.  Only if the simultaneous distinct users cannot
    be supported does C_Login have to return this value.  Note that this error
    code generalizes to true multi-user tokens.
    """


class WrappedKeyInvalid(PKCS11Error):
    pass


class WrappedKeyLenRange(PKCS11Error):
    pass


class WrappingKeyHandleInvalid(PKCS11Error):
    pass


class WrappingKeySizeRange(PKCS11Error):
    pass


class WrappingKeyTypeInconsistent(PKCS11Error):
    pass

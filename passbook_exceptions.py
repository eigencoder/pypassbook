import traceback


BASE_PASSBOOK_EXP_NUMBER = 100

class PassException(Exception):
    e_mnemonic = 'ERR_UNDEFINED'
    e_baseMsg = 'Undefined error'
    e_detailedMsg = ''
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER # match with error in error catalog

    def __init__(self, context=''):
        super(PassException, self).__init__()
        self.e_context = context
        self.e_trace = traceback.extract_stack()[:-1]


class ExpIncorrectPassword(PassException):
    e_mnemonic = 'PB_EXP_PASSWORD'
    e_baseMsg = 'Incorrect password'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 1

class ExpCertificateNotFound(PassException):
    e_mnemonic = 'PB_CERT_NOTFOUND'
    e_baseMsg = 'Certificate not found'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 2

class ExpManifestNotFound(PassException):
    e_mnemonic = 'PB_MANIFEST_NOTFOUND'
    e_baseMsg = 'Manifest not found'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 3

class ExpSignatureNotFound(PassException):
    e_mnemonic = 'PB_SIG_NOTFOUND'
    e_baseMsg = 'Signature not found'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 4

class ExpFileNotFound(PassException):
    e_mnemonic = 'PB_FILE_NOT_FOUND'
    e_baseMsg = 'Required file not found'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 5

class ExpPathAlreadyExists(PassException):
    e_mnemonic = 'PB_PATH_ALREADY_EXISTS'
    e_baseMsg = 'Temporary path is not available as it already exists'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 10

class ExpPathNotAvailable(PassException):
    e_mnemonic = 'PB_PATH_NOT_AVAILABLE'
    e_baseMsg = 'Path is not available'
    e_errCatalogNumber = BASE_PASSBOOK_EXP_NUMBER + 11

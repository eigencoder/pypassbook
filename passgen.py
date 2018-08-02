from hashlib import sha1
from subprocess import call
from uuid import uuid4

import errno
import json
import logging
import shutil
import os
import zipfile

import passbook_exceptions as pbExceptions

#Names based on Apple requirements
MANIFEST = "manifest.json"
SIGNATURE = "signature" #Filename must be 'signature' for Apple to load the pass

#Generated by developer
CERTIFICATE = "certificate.pem"
KEY_FILE = "key.pem"
PASSWORD = "1234" # CHANGE THIS FOR YOUR PROJECT!

SAVE_TMP_FILES = False #Will still keep files on exceptions due to _cleanup not being called (interrupted)

class Pass(object):
    def __init__(self, pass_name, files=(), auto_generate=False, allow_overwrite=False):
        """
        files: set/list of file names to be included in the compressed pass
        pass_name: barcode or username+barcode?
        destination: folder
        """
        self.files = set(files) #Always add icon.png and logo.png?
        self.pass_name = pass_name
        self.manifest_filename = MANIFEST
        self.signature_filename = SIGNATURE
        self.password = PASSWORD

        #Use file streams / strings instead of file-names?
        #Use https://github.com/gourneau/SpiderOak-zipstream if GPL3 is compatible with OutboxAXS's policies (probably not?)

        #Path for all temporary files. Must not put all 'manifest.json' in the same folder and be thread-safe!
        self._create_tmp_folder()

        #Make sure pass doesn't already exists
        if not allow_overwrite:
            if os.path.exists(self.pass_name):
                raise pbExceptions.ExpPathNotAvailable("Pass Name is already taken.")

        if auto_generate:
            self.generate()

    def _create_tmp_folder(self):
        self.tmp_path = "tmp_" + str(uuid4().hex[:16])
        try: #os.path.exists is not thread-safe. Use try/except
            os.makedirs(self.tmp_path)
            logging.debug("Added path: %s", self.tmp_path)
        except OSError as err:
            if err.errno == errno.EEXIST:
                raise pbExceptions.ExpPathAlreadyExists(
                    "Temporary path %s already exists, cannot proceed to create and use as tmp folder. Note: _create_tmp_folder should only be called once." % self.tmp_path
                )
            else:
                raise err

        #Update manifest_filename to include path
        self.manifest_filename = os.path.join(self.tmp_path, self.manifest_filename)
        self.signature_filename = os.path.join(self.tmp_path, self.signature_filename)

    def _cleanup(self):
        if (not SAVE_TMP_FILES) and os.path.exists(self.tmp_path):
            logging.debug("Removing path: %s", self.tmp_path)
            shutil.rmtree(self.tmp_path)

    def generate(self):
        self.gen_manifest()
        self.sign()
        self.compress()

        logging.info("Pass %s Generated", self.pass_name)
        self._cleanup()

    def gen_manifest(self):
        """ Build Manifest file.
        Go through each file and get their signatures
        """
        manifest = {}

        if not self.files:
            logging.warning("No files found to generate the manifest.")

        for file_name in self.files:
            with open(file_name) as f:
                file_data = f.read()
                sig = sha1(file_data).hexdigest() #ToDo: Once everything works, try to switch to sha512?
                manifest[file_name] = sig

        with open(self.manifest_filename, 'w') as manifest_handler:
            json.dump(manifest, manifest_handler, ensure_ascii=False)

        logging.debug("Manifest generated: %s", self.manifest_filename)

    def confirm_signed(self):
        if not self.signature_filename or not os.path.exists(self.signature_filename):
            raise pbExceptions.ExpSignatureNotFound(
                "Unable to confirm signature, file '%s' not found. Check path." % self.signature_filename
            )
        params = [
            'openssl', 'smime',
            '-verify',
            '-in', self.signature_filename,
            '-content', self.manifest_filename,
            '-inform', 'der',
            '-noverify' #-noverify means to ignore certificate's chain, use this at your own risk!
            ]

        ret = call(params, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb')) #Make this call silently
        if ret == 0:
            return True
        else:
            if ret == 4: #This shouldn't happen since it is covered above
                raise pbExceptions.ExpSignatureNotFound("Unable to confirm signature, file '%s' not found." % self.signature_filename)
            return False

    def compress(self):
        """ Zip all files. Must be called AFTER signature.
            Will create the file named from self.pass_name
        """
        #Make sure manifest and signature are included
        to_compress = {self.manifest_filename, self.signature_filename} | self.files

        if not self.confirm_signed():
         raise pbExceptions.ExpSignatureNotFound("No valid signature found. Certificate, key, or their associated password may not be valid.")

        with zipfile.ZipFile(self.pass_name, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for uncompressed_file in to_compress:
                zipped.write(uncompressed_file)

    def _openssl_smime(self, password, certificate, key):
        """
        Use OpenSSL directly to sign (generate signature)
        """
        if not certificate:
            raise ValueError("Bad parameter. Must pass a certificate name.")
        if not self.manifest_filename:
            raise ValueError("Bad parameter. Must have a manifest name to sign.")

        if not os.path.exists(certificate):
            raise pbExceptions.ExpCertificateNotFound("Certificate file required for signature not found.")
        if not os.path.exists(self.manifest_filename):
            raise pbExceptions.ExpManifestNotFound("Manifest file required for signature not found.")

        params = ['openssl', 'smime',
                  '-binary',
                  '-sign',
                  '-certfile', 'wwdr.pem',
                  '-signer', certificate, #'certificate.pem',
                  '-inkey', key, #'key.pem',
                  '-in', self.manifest_filename, #'manifest.json',
                  '-out', self.signature_filename, #'signature',
                  '-outform', 'DER',
                  '-passin', 'pass:'+password, ]
        ret = call(params, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb')) #Make this call silently
        if ret == 2:
            raise pbExceptions.ExpIncorrectPassword("Unable to sign manifest with given information. Incorrect password provided.")
        elif ret != 0:
            raise Exception("Unknown exception number '%s' while trying to sign manifest." % ret)

    def sign(self):
        """ Generate signature file, which authenticates the pass.
        Once signed, no file can be modified without re-signing.
        """
        if not self.password:
            logging.warning("Warning: no password set.")

        self._openssl_smime(password=self.password, certificate=CERTIFICATE, key=KEY_FILE)


    def add_file(self, filename):
        """ Add a file to the pass."""
        if not os.path.exists(filename):
            raise pbExceptions.ExpFileNotFound("Attempted to added file which could not be found.")
        self.files.add(filename)



# Helper methods
# """
# Generate files necessary for pass signing:
# ##openssl pkcs12 -in "My PassKit Cert.p12" -clcerts -nokeys -out certificate.pem
# ##openssl pkcs12 -in "My PassKit Cert.p12" -nocerts -out key.pem
#
# openssl pkcs12 -passin pass:"somepass" -in "mycert.p12" -clcerts -nokeys -out certificate.pem
# openssl pkcs12 -passin pass:"somepass" -in "mycert.p12" -nocerts -out key.pem -passout pass:"somepass"
# openssl smime -binary -sign -certfile WWDR.pem -signer certificate.pem -inkey key.pem -in manifest.json -out signature -outform DER -passin pass:"somepass"
# """
def generate_certificate_file(passkit_cert_p12, cert_name="certificate.pem"):
    ret = call(['openssl', 'pkcs12', '-in', passkit_cert_p12, '-clcerts', '-nokeys', '-out', cert_name])
    assert ret == 0, "Failed to generate pkcs12 certificate"

def generate_key_file(passkit_cert_p12, key_name="key.pem"):
    ret = call(['openssl', 'pkcs12', '-in', passkit_cert_p12, '-nocerts', '-out', key_name])
    assert ret == 0, "Failed to generate pkcs12 key file"

import unittest

from uuid import uuid4

import os
import passgen

import passbook_exceptions as pbExceptions

ICON = "test_assets/icon.png"
LOGO = "test_assets/logo.png"
JSON_PASS = "test_assets/pass.json"

# NOTE:

def _files_content_equal(file1, file2, trim_after=None):
    """ Give two file names and compare their contents.
    trim_after allows to compare the beginning of files, such as signatures where the end (>2900) changes every time
    """
    with open(file1, 'r') as file1_handler:
        file1_str = file1_handler.read()

    with open(file2, 'r') as file2_handler:
        file2_str = file2_handler.read()

    if trim_after:
        return file1_str[:trim_after] == file2_str[:trim_after]

    return file1_str == file2_str

def cleanup_pass(pass_object):
    """ Always call this with any Pass generated (including custom Pass() in tests) """
    pass_object._cleanup()
    if os.path.exists(pass_object.pass_name):
        os.remove(pass_object.pass_name)


class PassbookTest(unittest.TestCase):

    def setUp(self):
        file_list = [LOGO, ]
        tmp_pass_name = "tmp_" + str(uuid4().hex[:8]) +".pkpass"
        self.pass_obj = passgen.Pass(tmp_pass_name, file_list)

    def tearDown(self):
        #TODO Even on exception, remove temporary files
        cleanup_pass(self.pass_obj)

    def test_init(self):
        p = self.pass_obj
        self.assertEqual(os.path.basename(p.manifest_filename),
                         "manifest.json",
                         "Apple / Passbook requires manifest file to be named manifest.json")

        # Update this number if setUp.file_list gets changed
        self.assertTrue(len(p.files) == 1, "Exactly one file was given but %s found" % len(p.files))
        #p._cleanup() #If test passed, we no longer need the tmp_ folder

    def test_generate_manifest(self):
        p = self.pass_obj
        # Do NOT move this file to test_assets, it would get signed and added to the manifest
        expected_manifest_json = "test_expected/manifest.json.expected"
        #Check that manifest doesn't already exist
        self.assertFalse(os.path.exists(p.manifest_filename), "Manifest should not already exist.")

        #Generate manifest
        p.gen_manifest()

        #Check that manifest now exists and looks as expected
        self.assertTrue(os.path.exists(p.manifest_filename), "Manifest should have been created")

        self.assertTrue(os.path.exists(expected_manifest_json), "Need an expected result file to run this test. Please provide")

        #Compare files directly
        self.assertTrue(_files_content_equal(expected_manifest_json, p.manifest_filename), "Manifest file differs from expected")

    @unittest.skip("To improve: use a rexeg and openssl to confirm signature")
    def test_sign(self):
        p = self.pass_obj
        # Do NOT move this file to test_assets, it would get signed and added to the manifest
        #TODO THIS FILE MUST BE ADDED
        expected_file = "test_expected/signature.expected"
        p.gen_manifest() #Build manifest, required to sign
        p.sign()

        #Load signatures and check they are the same (ending will always change, so trim after 2800 characters)
        self.assertTrue(_files_content_equal(expected_file, p.signature_filename, trim_after=2800),
                        "Signature file differs from expected")
        self.assertTrue(p.confirm_signed(), "Signature failed verification, check that it is valid")

    def test_openssl_smime_bad_cert_fails(self):
        p = self.pass_obj
        p.gen_manifest() #Build manifest, required to sign

        #Call _openssl_smime directly to change standard value
        certificate = "this_path_should_not_exist.fail/certificate.pem"
        key = "key.pem"
        with self.assertRaises(pbExceptions.ExpCertificateNotFound):
            p._openssl_smime(password=p.password, certificate=certificate, key=key)

    def test_sign_bad_cert_fails(self):
        """ Overwrite certificate name and make sure correct exception is raised """
        original_value = passgen.CERTIFICATE
        passgen.CERTIFICATE = "this_path_should_not_exist.fail/certificate.pem"
        file_list = [LOGO, ]
        tmp_pass_name = "tmp_" + str(uuid4().hex[:8]) +".pkpass"
        #Build local pass to use new (temporary) values
        p = passgen.Pass(tmp_pass_name, file_list)
        p.gen_manifest() #Build manifest, required to sign
        with self.assertRaises(pbExceptions.ExpCertificateNotFound):
            p.sign()

        cleanup_pass(p) #Local Pass tmp files need to be deleted

        passgen.CERTIFICATE = original_value

    def test_sign_before_build_fails(self):
        p = self.pass_obj
        #Without building manifest first!
        p.manifest_filename = "this_path_should_not_exist.fail"
        with self.assertRaises(pbExceptions.ExpManifestNotFound):
            p.sign()

    def test_sign_no_manifest_fails(self):
        p = self.pass_obj
        p.gen_manifest() #Build manifest, then remove it
        p.manifest_filename = None #Remove link to manifest
        with self.assertRaises(ValueError):
            p.sign()

    def test_sign_bad_manifest_name_fails(self):
        p = self.pass_obj
        p.gen_manifest() #Build manifest, then remove it
        p.manifest_filename = "this_path_should_not_exist.fail" #Remove link to manifest
        with self.assertRaises(pbExceptions.ExpManifestNotFound):
            p.sign()

    def test_sign_wrong_pw_fails(self):
        p = self.pass_obj
        bad_pw = "12345"
        self.assertNotEqual(p.password, bad_pw, "Bad password must be bad for this test to work!")
        p.password = bad_pw #Switch correct pw with bad pw
        p.gen_manifest() #Build manifest
        with self.assertRaises(pbExceptions.ExpIncorrectPassword):
            p.sign()

    def test_integration_base(self):
        """ Include pass.json"""
        p = self.pass_obj
        p.add_file(JSON_PASS)
        p.add_file(ICON)
        p.gen_manifest() #Build manifest, required to sign
        p.sign()
        self.assertTrue(p.confirm_signed(), "Signature failed verification, check that it is valid")

    def test_generate_full(self):
        p = self.pass_obj
        p.add_file(JSON_PASS)
        p.add_file(ICON)

        p.generate() #cleans up temporary files
        #tmp files have already been deleted self.assertTrue(p.confirm_signed(), "Signature failed verification, check that it is valid")
        self.assertTrue(len(p.pass_name) > 0, "Must have a pass name for this test to make sense.")
        self.assertTrue(os.path.exists(p.pass_name), "Could not find pass named %s." % p.pass_name)


    def test_autogenerate(self):
        original_value = passgen.SAVE_TMP_FILES
        passgen.SAVE_TMP_FILES = True
        file_list = [LOGO, JSON_PASS, ICON]
        tmp_pass_name = "tmp_" + str(uuid4().hex[:8]) +".pkpass"
        p = passgen.Pass(tmp_pass_name, file_list, auto_generate=True)
        self.assertTrue(p.confirm_signed(), "Signature failed verification, check that it is valid")
        p._cleanup() #Local pass tmp files need to be deleted
        passgen.SAVE_TMP_FILES = original_value #Return to original value

        cleanup_pass(p)
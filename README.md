# PyPassbook

A simple .pkpass generator for Apple's Passbook. Easily generate "mobile tickets" for Apple devices!

PyPassbook uses standard Openssl and no other library so it will work on non-osx machines. No need to audit extra libraries, and this project is small enough for a security engineer to review quickly.

Once you have generated your `pass.json` payload, use this project to generate the compressed and signed `.pkpass` to be used by your customers.

  

## Setup

#### Openssl
Openssl is required for signing the manifest.
```
brew install openssl
```

#### Private Cert/Key
DO NOT USE THE DEFAULT MOCK KEY/CERTIFICATES. They are here for testing purposes and demo only. 
**They are not safe, nor valid**. The password is '1234'.

To sign the manifest, you must have a certificate and a key. You can generate the following files and add them to the root of this project or add a symbolic link.

- `passkit_cert_p12` 
  * Get from an active dev account on Apple's developer website
- `certificate.pem` 
  * Generate with helper method `generate_key_file(passkit_cert_p12)`
- `key.pem` 
  * Generate with helper method `generate_key_file(passkit_cert_p12)`

**WARNING: THESE FILES MUST REMAIN PRIVATE.**
**Do not commit them to public repositories!** 

Without these files, some tests will fail with the following error. `ExpCertificateNotFound`

#### Password
Make sure to edit `passgen.py:PASSWORD` variable and set it to the value required by your key.pem

## Usage
Assuming you have a pass.json and an assets list
```buildoutcfg
import passgen
        
file_list = [logo_file_path, ] # Assets
random_pass_name = "event-name-here-%s.pkpass" % str(uuid4().hex[:8]) 
pass_obj = passgen.Pass(pass_name, file_list, auto_generate=True)
```

## Tests

##### Running tests
```buildoutcfg
$ nosetests
```

##### Certificate
As mentioned in Setup, you will need a certificate and key in the project's root for all tests to pass.  

##### Signature
If you intend to test the signature code, you will need to add a copy of the signature in `test_expected/signature.expected`. You can find one in a temporary folder. 
First test it by importing the resulting code to an Apple device which has the necessary developer profile.

##### Mock Cert/Key
To generate a mock certificate and key, you can run the following code. It will not be valid for passes and pass will be rejected by iOS.

```openssl req -x509 -newkey rsa:4096 -keyout key.pem -out certificate.pem -days 9999```
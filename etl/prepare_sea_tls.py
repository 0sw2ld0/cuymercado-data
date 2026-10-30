"""Complete a missing intermediate only after validation against Mozilla trust roots."""
import hashlib,os,subprocess,tempfile
from pathlib import Path
import certifi

def prepare():
    intermediate=Path(__file__).resolve().parent/'certs/sectigo-dv-r36.pem'
    # Never trust a server leaf or a self-signed replacement root.
    # The intermediate must chain to an independently trusted Mozilla root first.
    subprocess.run(['openssl','verify','-CAfile',certifi.where(),str(intermediate)],check=True)
    bundle=Path(tempfile.gettempdir())/'cuymercado-public-ca.pem'
    bundle.write_bytes(Path(certifi.where()).read_bytes()+b'\n'+intermediate.read_bytes())
    if os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'],'a') as out:out.write(f'CURL_CA_BUNDLE={bundle}\n')
    print('Verified CA bundle:',bundle)
    return bundle
if __name__=='__main__':prepare()

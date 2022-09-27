import os
import re
from hashlib import sha256
from json import loads
from pathlib import Path
from urllib.request import urlopen, urlretrieve


def get_config():
    download_url: str = f'https://get.gravitational.com/teleport-{get_latest_version()}-1.x86_64.rpm'
    return {
        'download_url': download_url,
        'signature_url': download_url + '.sha256',
        'target_file': '/srv/repo/tools/' + Path(download_url).name,
    }


def get_latest_version() -> str:
    versions: list = []
    with urlopen('https://api.github.com/repos/gravitational/teleport/releases') as response:
        for record in loads(response.read()):
            if re.match(r'v[.\d]+$', record['tag_name']):
                versions.append(tuple([int(n) for n in re.sub(r'^v', '', record['tag_name']).split('.')]))
    return '.'.join(str(n) for n in sorted(versions)[-1])


def teleport_file_download(config: dict):
    if Path(config['target_file']).exists():
        print(f"Latest version already exists: '{config['target_file']}'. Not downloading.")
    else:
        print(f'Downloading from {config["download_url"]} to {config["target_file"]}')
        urlretrieve(config["download_url"], config["target_file"])


def get_sha256sum_file(file: str) -> str:
    sha256sum = sha256()
    with open(file, 'rb') as fh:
        while True:
            data = fh.read(65536)
            if not data:
                return sha256sum.hexdigest()
            sha256sum.update(data)


def teleport_signature_verify(config: dict):
    print(f'Comparing signature of {config["target_file"]} with {config["signature_url"]}')
    with urlopen(config['signature_url']) as response:
        sha256sum_teleport = response.read(64).decode("utf-8")

    sha256sum_dl_file = get_sha256sum_file(config["target_file"])
    if sha256sum_dl_file == sha256sum_teleport:
        print(f'File {config["target_file"]} has a valid checksum')
    else:
        print(f'File {config["target_file"]} has an invalid checksum. Deleting file.')
        os.remove(config['target_file'])


def teleport_file_cleanup(config):
    print(f'Cleaning up old versions before {config["target_file"]}')
    for file in Path('/srv/repo/tools/').glob('teleport-*.rpm'):
        if file.name != Path(config['target_file']).name:
            os.remove(file)


def main():
    config: dict = get_config()
    teleport_file_download(config)
    teleport_signature_verify(config)
    teleport_file_cleanup(config)


if __name__ == '__main__':
    main()

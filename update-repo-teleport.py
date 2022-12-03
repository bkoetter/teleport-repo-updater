import os
import re
from hashlib import sha256
from json import loads
from pathlib import Path
from sys import exit
from urllib.error import HTTPError
from urllib.request import Request, urlopen, urlretrieve

from typing import List


def get_config(download_location: str) -> dict:
    download_url: str = f'https://{download_location}/teleport-{get_latest_version()}-1.x86_64.rpm'
    signature_url: str = f'https://get.gravitational.com/teleport-{get_latest_version()}-1.x86_64.rpm.sha256'
    return {
        'download_url': download_url,
        'signature_url': signature_url,
        'target_file': '/srv/repo/tools/' + Path(download_url).name,
    }


def get_latest_version() -> str:
    versions: list = []
    with urlopen('https://api.github.com/repos/gravitational/teleport/releases') as response:
        for record in loads(response.read()):
            if re.match(r'v[.\d]+$', record['tag_name']):
                versions.append(tuple([int(n) for n in re.sub(r'^v', '', record['tag_name']).split('.')]))
    return '.'.join(str(n) for n in sorted(versions)[-1])


def teleport_file_download(config: dict) -> bool:
    if Path(config['target_file']).exists():
        print(f"Latest version already exists: '{config['target_file']}'. Not downloading.")
        exit(0)
    else:
        print(f'Downloading from {config["download_url"]} to {config["target_file"]}')
        try:
            urlretrieve(config["download_url"], config["target_file"])
            return True
        except Exception as e:
            print(f'Error: {e}')
            return False


def get_sha256sum_file(file: str) -> str:
    sha256sum = sha256()
    with open(file, 'rb') as fh:
        while True:
            data = fh.read(65536)
            if not data:
                return sha256sum.hexdigest()
            sha256sum.update(data)


def teleport_signature_verify(config: dict) -> None:
    print(f'Comparing signature of {config["target_file"]} with {config["signature_url"]}')
    try:
        req = Request(url=config['signature_url'], headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req) as response:
            sha256sum_teleport = response.read(64).decode("utf-8")
    except HTTPError as e:
        if e.code == 404:
            print(f'Error: Signature file not found: {config["signature_url"]}')
            sha256sum_teleport: str = input('Enter sha256 matching signature from download page: ')
        else:
            print(f'Error: Failed to retrieve signature file from {config["signature_url"]}: {e}')
            cleanup_and_exit(1, config)

    sha256sum_dl_file = get_sha256sum_file(config["target_file"])
    if sha256sum_dl_file == sha256sum_teleport:
        print(f'File {config["target_file"]} has a valid checksum')
    else:
        print(f'File {config["target_file"]} has an invalid checksum. Deleting file.')
        os.remove(config['target_file'])


def teleport_file_cleanup(config) -> None:
    target_dir = Path(config['target_file']).parent
    file_names = list(target_dir.glob('teleport-*.rpm'))
    if len(file_names) <= 3:
        return

    print(f'Cleaning up old versions before {config["target_file"]}. Keeping 3 latest versions.')
    for file in sorted(file_names)[:-3]:
        if file.name != Path(config['target_file']).name:
            print(f'Not deleting downloaded {file}! Inspection required.')
            continue
        print(f'Deleting previously downloaded {file}')
        try:
            file.unlink()
        except OSError as e:
            print(f'Error: {file} : {e.strerror}')


def cleanup_and_exit(exit_code: int, config: dict) -> None:
    # remove downloaded file if it exists
    try:
        os.remove(config['target_file'])
    except OSError as err:
        print(f'Error: {err.strerror}')
    finally:
        exit(exit_code)


def main():
    download_locations: List[str] = ['cdn.teleport.dev']
    for download_location in download_locations:
        config: dict = get_config(download_location)
        if not teleport_file_download(config):
            continue
        teleport_signature_verify(config)
        teleport_file_cleanup(config)


if __name__ == '__main__':
    main()

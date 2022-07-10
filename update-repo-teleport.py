from json import loads
from urllib.request import urlopen


def main():
    with urlopen('https://api.github.com/repos/gravitational/teleport/releases') as response:
        for record in loads(response.read()):
            print(record['tag_name'])


if __name__ == '__main__':
    main()

# import requests
#
# response = requests.post('http://127.0.0.1:5000/check')
#
# print(response.json())
from pathlib import Path
Path(__file__).parent.joinpath('./Download Manager.exe')

print(f'{Path(__file__).parent.joinpath('./Download Manager.exe')}')

import os
print(__file__)
print(os.path.join(os.path.dirname(__file__), '..'))
print(os.path.dirname(os.path.realpath(__file__)))
print(os.path.abspath(os.path.dirname(__file__)))
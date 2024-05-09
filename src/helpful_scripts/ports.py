import json
from requests import get

onos_ip = '192.168.43.18'


def get_device(number):
    h = str(hex(number)[2:])
    return 'of:' + '0' * (16 - len(h)) + h


def main():
    with open('network.json', 'r') as file:
        content = json.loads(file.read())
    switches = [(city, get_device(i + 1)) for i, city in
                enumerate(content['cities'])]
    response_links = get(f'http://{onos_ip}:8181/onos/v1/links',
                         headers={'Accept': 'application/json'},
                         auth=('onos', 'rocks')).json()['links']
    for link in response_links:
        city_a = next(
            s[0] for s in switches if s[1] == link['src']['device'])
        city_b = next(
            s[0] for s in switches if s[1] == link['dst']['device'])
        for i, l in enumerate(content['links']):
            if l['city_a'] == city_a and l['city_b'] == city_b:
                content['links'][i]['port_a'] = link['src']['port']
                content['links'][i]['port_b'] = link['dst']['port']
                break
            if l['city_b'] == city_a and l['city_a'] == city_b:
                content['links'][i]['port_a'] = link['dst']['port']
                content['links'][i]['port_b'] = link['src']['port']
                break
    with open('network.json', 'w') as file:
        file.write(json.dumps(content, sort_keys=True, indent=4))


if __name__ == '__main__':
    main()

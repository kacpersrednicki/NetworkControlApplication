import json
from math import cos, sin, atan2, sqrt, radians
from mininet.topo import Topo

cities = {
    'Malmo': (55.605, 13.003), 'Berlin': (52.576, 13.398),
    'Gdansk': (54.389, 18.686), 'Hanower': (52.374, 9.665),
    'Praga': (50.145, 14.427), 'Norymberga': (49.484, 11.067),
    'Wieden': (48.224, 16.370), 'Ostrawa': (49.829, 18.260),
    'Zagrzeb': (45.825, 15.979), 'Graz': (47.072, 15.439)
}


links = [
    ('Malmo', 'Berlin'), ('Hanower', 'Berlin'), ('Berlin', 'Gdansk'),
    ('Berlin', 'Praga'), ('Praga', 'Norymberga'), ('Praga', 'Wieden'),
    ('Wieden', 'Ostrawa'), ('Wieden', 'Zagrzeb'), ('Zagrzeb', 'Graz'),
    ('Malmo', 'Hanower'), ('Hanower', 'Norymberga'), ('Hanower', 'Praga'),
    ('Norymberga', 'Wieden'), ('Norymberga', 'Zagrzeb'), ('Praga', 'Ostrawa'),
    ('Berlin', 'Ostrawa'), ('Gdansk', 'Ostrawa'), ('Malmo', 'Gdansk'),
    ('Graz', 'Wieden')
]


def get_delay(city_a, city_b):
    lat1, lon1 = cities[city_a]
    lat2, lon2 = cities[city_b]
    radius = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = radius * c * sqrt(2) / 200
    return distance


class MyTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        switches = {}
        bandwidth = 10
        result = {'cities': [], 'links': []}
        for i, city in enumerate(cities):
            switch = self.addSwitch(f's{i + 1}')
            host = self.addHost(f'h{i + 1}')
            self.addLink(switch, host, delay='0.1ms')
            switches[city] = switch
            result['cities'].append(city)
        for city_a, city_b in links:
            delay = get_delay(city_a, city_b)
            delay_str = f'{delay:.2f}ms'
            self.addLink(switches[city_a], switches[city_b], bw=bandwidth,
                         delay=delay_str)
            result['links'].append(
                {'city_a': city_a, 'city_b': city_b, 'delay': delay,
                 'bandwidth': bandwidth})
        with open('network.json', 'w') as file:
            file.write(json.dumps(result, sort_keys=True, indent=4))


topos = {'mytopo': lambda: MyTopo()}

import json

result = {'flows': []}


def add_flow(device, out_port, in_port_crit, dest_crit):
    result['flows'].append({
        'priority': 40000,
        'timeout': 0,
        'isPermanent': True,
        'deviceId': f'of:000000000000000{device}',
        'treatment': {
            'instructions': [
                {
                    'type': 'OUTPUT',
                    'port': f'{out_port}'
                }
            ]
        },
        'selector': {
            'criteria': [
                {
                    'type': 'IN_PORT',
                    'port': f'{in_port_crit}'
                },
                {
                    'type': 'ETH_TYPE',
                    'ethType': '0x0800'
                },
                {
                    'type': 'IPV4_DST',
                    'ip': f'10.0.0.{dest_crit}/32'
                }
            ]
        }
    })


def ex1_connections():
    # 1 - 10
    add_flow(1, 2, 1, 10)
    add_flow(2, 5, 2, 10)
    add_flow(5, 4, 2, 10)
    add_flow(7, 4, 2, 10)
    add_flow(9, 3, 2, 10)
    add_flow('a', 1, 2, 10)
    add_flow('a', 2, 1, 1)
    add_flow(9, 2, 3, 1)
    add_flow(7, 2, 4, 1)
    add_flow(5, 2, 4, 1)
    add_flow(2, 2, 5, 1)
    add_flow(1, 1, 2, 1)
    # 4 - 6
    add_flow(4, 2, 1, 6)
    add_flow(2, 5, 3, 6)
    add_flow(5, 3, 2, 6)
    add_flow(6, 1, 2, 6)
    add_flow(6, 2, 1, 4)
    add_flow(5, 2, 3, 4)
    add_flow(2, 3, 5, 4)
    add_flow(4, 1, 2, 4)
    # 3 - 7
    add_flow(3, 2, 1, 7)
    add_flow(2, 5, 4, 7)
    add_flow(5, 4, 2, 7)
    add_flow(7, 1, 2, 7)
    add_flow(7, 2, 1, 3)
    add_flow(5, 2, 4, 3)
    add_flow(2, 4, 5, 3)
    add_flow(3, 1, 2, 3)


def ex2_connections():
    # 4 - 6
    add_flow(4, 4, 1, 6)
    add_flow(6, 1, 3, 6)
    add_flow(6, 3, 1, 4)
    add_flow(4, 1, 4, 4)
    # 3 - 7
    add_flow(3, 3, 1, 7)
    add_flow(8, 2, 5, 7)
    add_flow(7, 1, 3, 7)
    add_flow(7, 3, 1, 3)
    add_flow(8, 5, 2, 3)
    add_flow(3, 1, 3, 3)
    # 1 - 5
    add_flow(1, 2, 1, 5)
    add_flow(2, 5, 2, 5)
    add_flow(5, 1, 2, 5)
    add_flow(5, 2, 1, 1)
    add_flow(2, 2, 5, 1)
    add_flow(1, 1, 2, 1)


# ex1_connections()
ex2_connections()
with open('result.json', 'w') as file:
    file.write(json.dumps(result, sort_keys=True, indent=4))

import json
from copy import copy
from requests import post, delete
from networkx import Graph, shortest_path, NodeNotFound


class Switch:
    def __init__(self, name, index):
        self.name = name
        self.number = index + 1
        self.ip = f'10.0.0.{self.number}/32'
        h = str(hex(self.number)[2:])
        self.device = 'of:' + '0' * (16 - len(h)) + h


class Link:
    def __init__(self, index, link_data, get_switch_function):
        self.index = index
        self.switch_a = get_switch_function(link_data['city_a'])
        self.port_a = link_data['port_a']
        self.switch_b = get_switch_function(link_data['city_b'])
        self.port_b = link_data['port_b']
        self.delay = link_data['delay']
        self.max_bandwidth = link_data['bandwidth']
        self.tcp_sessions = []
        self.udp_sessions = []
        self.ping_sessions = []

    def flip(self):
        result = copy(self)
        result.switch_a, result.switch_b = result.switch_b, result.switch_a
        result.port_a, result.port_b = result.port_b, result.port_a
        return result

    def add_session(self, session):
        if session.session_type == 'UDP':
            self.udp_sessions.append(session)
        elif session.session_type == 'TCP':
            self.tcp_sessions.append(session)
        else:
            self.ping_sessions.append(session)

    def remove_session(self, session):
        if session.session_type == 'UDP':
            self.udp_sessions.remove(session)
        elif session.session_type == 'TCP':
            self.tcp_sessions.remove(session)
        else:
            self.ping_sessions.remove(session)

    def estimate_bandwidth(self, session):
        if session.session_type == 'PING':
            return 0
        if session.session_type == 'UDP':
            return session.bandwidth
        return (self.max_bandwidth - sum(
            s.bandwidth for s in self.udp_sessions)) / len(self.tcp_sessions)

    def max_possible(self):
        tcp_min = max((s.bandwidth for s in self.tcp_sessions),
                      default=0) * len(self.tcp_sessions)
        udp = self.max_bandwidth - tcp_min - sum(
            s.bandwidth for s in self.udp_sessions)
        tcp_part = (self.max_bandwidth - sum(
            s.bandwidth for s in self.udp_sessions)) / (
                            len(self.tcp_sessions) + 1)
        if all(tcp_part >= s.bandwidth for s in self.tcp_sessions):
            return udp, tcp_part
        return udp, 0

    def can_handle(self, session):
        if session.session_type == 'PING':
            return True
        udp_max, tcp_max = self.max_possible()
        if session.session_type == 'UDP':
            return session.bandwidth <= udp_max
        return session.bandwidth <= tcp_max


class Session:
    def __init__(self, host_a, host_b, session_type, requested_bandwidth):
        self.host_a = host_a
        self.host_b = host_b
        self.session_type = session_type
        self.bandwidth = requested_bandwidth
        self.flows = []
        self.path = []

    def set_path(self, path):
        self.path = path

    def add_flows(self, result):
        self.flows.extend(result['flows'])


def create_flow(device, out_port, in_port_crit, src_crit, dest_crit,
                session_type):
    result = {
        'priority': 40000,
        'timeout': 0,
        'isPermanent': True,
        'deviceId': device,
        'treatment': {
            'instructions': [
                {
                    'type': 'OUTPUT',
                    'port': out_port
                }
            ]
        },
        'selector': {
            'criteria': [
                {
                    'type': 'IN_PORT',
                    'port': in_port_crit
                },
                {
                    'type': 'ETH_TYPE',
                    'ethType': '0x0800'
                },
                {
                    'type': 'IPV4_SRC',
                    'ip': src_crit
                },
                {
                    'type': 'IPV4_DST',
                    'ip': dest_crit
                }
            ]
        }
    }
    if session_type in ('TCP', 'UDP'):
        # noinspection PyTypeChecker
        result['selector']['criteria'].append({
            'type': 'IP_PROTO',
            'protocol': '6' if session_type == 'TCP' else '17'
        })
    return result


def generate_iperf(session):
    if session.session_type == 'PING':
        return
    ip = session.host_b.ip.split('/')[0]
    if session.session_type == 'TCP':
        content = (f"h{session.host_b.number} iperf -e -i 1 -s > listen.tx"
                   f"t &\nh{session.host_a.number} iperf -e -i 1 -c "
                   f"{ip} -N -S 0x08 -n 10M > send.txt &")
    else:
        content = (f"h{session.host_b.number} iperf -e -i 1 -s -u > listen.txt"
                   f" &\nh{session.host_a.number} iperf -e -i 1 -c "
                   f"{ip} -u -S 0x10 -t 10 -b 1024pps -l "
                   f"{session.bandwidth * 128} > send.txt &")
    with open('script.txt', 'w') as f:
        f.write(content)


class Manager:
    def __init__(self, network):
        self.onos_ip = ''
        with open(network, 'r') as file:
            content = json.loads(file.read())
        self.switches = [Switch(n, i) for i, n in
                         enumerate(content['cities'])]
        self.links = [Link(i, link, lambda s: self.get_switch(s)) for i, link
                      in enumerate(content['links'])]
        self.sessions = []

    def set_onos_ip(self, onos_ip):
        self.onos_ip = onos_ip

    def safe_shortest_path(self, graph, u, v):
        try:
            return shortest_path(graph, u, v,
                                 weight=lambda _u, _v, l: self.links[
                                     l['link_index']].delay)
        except NodeNotFound:
            return []

    def find_shortest(self, session):
        network = Graph()
        for link in self.links:
            if link.can_handle(session):
                network.add_edge(link.switch_a.number, link.switch_b.number,
                                 link_index=link.index)
        return self.safe_shortest_path(network, session.host_a.number,
                                       session.host_b.number)

    def get_switch(self, city):
        return next(
            (s for s in self.switches if s.name.lower() == city.lower()), None)

    def get_link(self, switch_a_num, switch_b_num):
        if l := next((l for l in self.links if
                      l.switch_a.number == switch_a_num
                      and l.switch_b.number == switch_b_num), None):
            return l
        if l := next((l for l in self.links if
                      l.switch_a.number == switch_b_num
                      and l.switch_b.number == switch_a_num), None):
            return l.flip()

    def find_same_session(self, city_a, city_b, session_type):
        same_sessions = [s for s in self.sessions if
                         city_a == s.host_a and city_b == s.host_b
                         or city_a == s.host_b and city_b == s.host_a]
        if session_type == 'PING' and same_sessions:
            return True
        if any(s for s in same_sessions if
               s.session_type == session_type or s.session_type == 'PING'):
            return True

    def add_path(self, city_a, city_b, session_type, required_bandwidth):
        if self.find_same_session(city_a, city_b, session_type):
            print('Dla tych hostów istnieje już połączenie uniemożliwiające ut'
                  'worzenie takiej sesji')
            return
        session = Session(city_a, city_b, session_type, required_bandwidth)
        if not (path := self.find_shortest(session)):
            return None
        session.set_path(path)
        result = {'flows': []}
        links = [self.get_link(a, b) for a, b in zip(path, path[1:])]
        for link in links:
            link.add_session(session)
        result['flows'].append(create_flow(
            city_a.device, 1, links[0].port_a, city_b.ip, city_a.ip,
            session_type))
        result['flows'].append(create_flow(
            city_b.device, 1, links[-1].port_b, city_a.ip, city_b.ip,
            session_type))
        for i, link in enumerate(links):
            if i == 0:
                previous_port = '1'
            else:
                previous_port = links[i - 1].port_b
            result['flows'].append(create_flow(
                link.switch_a.device,
                link.port_a,
                previous_port,
                city_a.ip,
                city_b.ip,
                session_type
            ))
            if i == len(links) - 1:
                previous_port = '1'
            else:
                previous_port = links[i + 1].port_a
            result['flows'].append(create_flow(
                link.switch_b.device,
                link.port_b,
                previous_port,
                city_b.ip,
                city_a.ip,
                session_type
            ))
        response = post(f'http://{self.onos_ip}:8181/onos/v1/flows',
                        headers={'Accept': 'application/json',
                                 'Content-Type': 'application/json'},
                        data=json.dumps(result),
                        auth=('onos', 'rocks'))
        session.add_flows(response.json())
        self.sessions.append(session)
        return session

    def remove_session(self, removed):
        links = [self.get_link(a, b) for a, b in
                 zip(removed.path, removed.path[1:])]
        for link in links:
            link.remove_session(removed)
        self.sessions.remove(removed)
        for flow in removed.flows:
            delete(f'http://{self.onos_ip}:8181/onos/v1/flows/'
                   f'{flow["deviceId"]}/{flow["flowId"]}',
                   headers={'Accept': 'application/json'},
                   auth=('onos', 'rocks'))

    def display_session(self, session, session_id):
        return (f'[{session_id}]: Type: {session.session_type}, Requested: '
                f'{session.bandwidth} Mb/s, Estimate: '
                f'{self.get_estimate(session):.2f} Mb/s, Path: '
                f'{self.display_path(session.path)}')

    def display_path(self, path):
        path_str = ' -> '.join(self.switches[i - 1].name for i in path)
        delay = sum(self.get_link(a, b).delay for a, b in zip(path, path[1:]))
        return f'[{path_str}], Link delay: {delay:.2f} ms'

    def get_estimate(self, session):
        return min(self.get_link(a, b).estimate_bandwidth(session) for a, b in
                   zip(session.path, session.path[1:]))

    def test_between(self, city_a, city_b, session_type):
        if self.find_same_session(city_a, city_b, session_type):
            print('Dla tych hostów istnieje już połączenie uniemożliwiające ut'
                  'worzenie takiej sesji')
            return
        links = [(l, l.max_possible()) for l in self.links]
        index = 0 if session_type == 'UDP' else 1
        links.sort(key=lambda l: l[1][index], reverse=True)
        network = Graph()
        paths = {}
        while True:
            if not links:
                break
            current = links[0][1][index]
            while links and links[0][1][index] == current:
                l = links.pop(0)[0]
                network.add_edge(l.switch_a.number, l.switch_b.number,
                                 link_index=l.index)
            if path := self.safe_shortest_path(network, city_a.number,
                                               city_b.number):
                if tuple(path) not in paths:
                    paths[tuple(path)] = current
        result = [(p, m) for p, m in paths.items()]
        result.sort(key=lambda x: x[1])
        for p, m in result:
            print(f'Max: {m} Mb/s, Path: {self.display_path(p)}')

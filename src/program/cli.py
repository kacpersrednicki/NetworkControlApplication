from manager import Manager, generate_iperf
from codecs import open

manager = Manager('network.json')
with open('help.txt', 'r', 'utf-8') as file:
    help_message = file.read()
available_id = 0
sessions = {}
scheduled_commands = []


def get_onos_ip():
    try:
        with open('ip.txt', 'r') as f:
            ip = f.read()
    except IOError:
        ip = input('Podaj IP ONOS (utwórz plik ip.txt z wartością IP, by nie po'
                   'dawać go za każdym razem)\n')
    manager.set_onos_ip(ip)


def verify_args_length(expected, args):
    if len(args) != expected:
        print(f'Nieprawdiłowa liczba argumentów {len(args)}. Oczekiwano '
              f'{expected}')
        return False
    return True


def verify_city(city):
    if not (found := manager.get_switch(city)):
        print(f'Nie znaleziono hosta o nazwie "{city}"')
    return found


def verify_session_type(session_type):
    if (upper := session_type.upper()) not in ('TCP', 'UDP'):
        print(f'Nieprawidłowy typ sesji "{session_type}". Oczekiwano "TCP" l'
              f'ub "UDP"')
        return ""
    return upper


def verify_float(number):
    try:
        return float(number)
    except ValueError:
        print(f'Nieprawidłowy format liczby zmiennoprzecinkowej "{number}"')
        return None


def verify_int(number):
    try:
        return int(number)
    except ValueError:
        print(f'Nieprawidłowy format liczby "{number}"')
        return None


def verify_file(path):
    try:
        f = open(path, 'r')
        return f
    except OSError:
        print(f'Nie znaleziono pliku o nazwie "{path}"')
        return None


def print_help(args):
    if not verify_args_length(0, args):
        return
    print(help_message)


def print_hosts(args):
    if not verify_args_length(0, args):
        return
    print(', '.join(s.name for s in manager.switches))


def ping(args):
    global available_id
    if not verify_args_length(2, args):
        return
    if not (start_host := verify_city(args[0])):
        return
    if not (end_host := verify_city(args[1])):
        return
    if start_host == end_host:
        print('Sesja musi być realizowana pomiędzy dwoma różnymi hostami')
        return
    if not (session := manager.add_path(start_host, end_host, 'PING', 0)):
        print('Nie udało się utworzyć takiej ścieżki')
        return
    sessions[available_id] = session
    print('Utworzono nową ścieżkę:')
    print(manager.display_session(session, available_id))
    available_id += 1


def start_session(args):
    global available_id
    if not verify_args_length(4, args):
        return
    if not (start_host := verify_city(args[0])):
        return
    if not (end_host := verify_city(args[1])):
        return
    if start_host == end_host:
        print('Sesja musi być realizowana pomiędzy dwoma różnymi hostami')
        return
    if not (session_type := verify_session_type(args[2])):
        return
    if (required_bandwidth := verify_float(args[3])) is None:
        return
    if not (session := manager.add_path(start_host, end_host, session_type,
                                        required_bandwidth)):
        print('Nie udało się utworzyć takiej ścieżki')
        return
    generate_iperf(session)
    sessions[available_id] = session
    print('Utworzono nową ścieżkę:')
    print(manager.display_session(session, available_id))
    available_id += 1


def list_sessions(args):
    if not verify_args_length(0, args):
        return
    for i, s in sessions.items():
        print(manager.display_session(s, i))


def end_session(args):
    if not verify_args_length(1, args):
        return
    if (session_id := verify_int(args[0])) is None:
        return
    if session_id not in sessions:
        print(f'Nie ma sesji o ID {session_id}')
        return
    manager.remove_session(sessions.pop(session_id))
    print(f"Usunięto sesję")


def source_file(args):
    global scheduled_commands
    if not verify_args_length(1, args):
        return
    if not (f := verify_file(args[0])):
        return
    scheduled_commands = f.readlines() + scheduled_commands
    f.close()


def test_link(args):
    if not verify_args_length(3, args):
        return
    if not (host_a := verify_city(args[0])):
        return
    if not (host_b := verify_city(args[1])):
        return
    if not (session_type := verify_session_type(args[2])):
        return
    manager.test_between(host_a, host_b, session_type)


def exit_program(args):
    if not verify_args_length(0, args):
        return
    for s in sessions.values():
        manager.remove_session(s)
    print('Usunięto wszystkie ścieżki')
    exit()


def main():
    get_onos_ip()
    commands = {
        'help': print_help,
        'hosts': print_hosts,
        'ping': ping,
        'start': start_session,
        'list': list_sessions,
        'end': end_session,
        'source': source_file,
        'test': test_link,
        'exit': exit_program,
    }
    print('Wpisz "help" po listę poleceń')
    while True:
        if scheduled_commands:
            command = scheduled_commands.pop(0).strip()
            print(command)
            split = command.split(' ')
        else:
            split = input().split(' ')
        if split[0] not in commands:
            print('Nieprawidłowe polecenie, wpisz help po pomoc')
            continue
        commands[split[0]](split[1:])


if __name__ == '__main__':
    main()

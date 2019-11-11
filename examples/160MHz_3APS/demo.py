import zmq
import time
import random

customers = {
    b'STA_A1_C1': 1,
    b'STA_A2_C1': 1,
    b'STA_A3_C1': 1,
    b'STA_B1_C1': 1,
    b'STA_B1_C2': 1,
    b'STA_B1_C3': 1,
    b'STA_C1_C1': 1,
    b'STA_C1_C2': 1,
    b'STA_C2_C1': 1,
}


def can_switch_off(customer):
    if customers[customer] == 0:
        return False

    # Station needs at least one active customer
    sta = b'_'.join(customer.split(b'_')[0:-1])
    active_customers = list(filter(lambda c: c.startswith(sta) and customers[c] == 1, customers))

    if len(active_customers) < 2:
        return False

    return True


def can_switch_on(customer):
    if customers[customer] == 1:
        return False

    return True


def sendAction(socket, client, state):
    socket.send_multipart([client, state])
    socket.recv_multipart()


def main():
    client_ctrl_port = 8888
    hostname_managed = 'localhost'

    ctx = zmq.Context()

    req_managed = ctx.socket(zmq.REQ)
    req_managed.connect("tcp://{}:{}".format(hostname_managed, client_ctrl_port))

    while True:
        state = random.choice([b'on', b'off'])

        if state == b'on':
            candidates = list(filter(lambda c: can_switch_on(c), customers))
            if not candidates:
                continue

            client = random.choice(candidates)
            customers[client] = 1
        else:
            candidates = list(filter(lambda c: can_switch_off(c), customers))
            if not candidates:
                continue

            client = random.choice(candidates)
            customers[client] = 0

        print(client, state)
        sendAction(req_managed, client, state)
        time.sleep(20)


if __name__ == '__main__':
    main()
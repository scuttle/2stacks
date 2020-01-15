def get_bytes(url: str, port=80, maxlength=2800):

    import socket
    from time import sleep

    # Sanitize the url for old-school socket processing.
    url = url.replace('http://', '')
    url_parts = url.split('/', 1)
    hostname = url_parts[0]
    path = url_parts[1]

    MESSAGE = \
        "GET /" + path + " HTTP/1.1\r\n" \
        "HOST: " + hostname + "\r\n" \
        "User-Agent: 2stacks-lambda/0.0.1\r\n" \
        "Accept: */*\r\n\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a socket
    sock.connect((hostname, port))  # Connect to remote socket at given address
    msg = MESSAGE.encode('utf-8')
    sock.send(msg)  # Let's begin the transaction

    sleep(0.1)

    # Keep reading from socket till max limit is reached
    curr_size = 0
    result = ""
    while curr_size < maxlength:
        result += sock.recv(maxlength - curr_size).decode('utf-8')
        curr_size = len(result)

    sock.close()  # Mark the socket as closed

    return result


def fetch(data: dict, wikidot_site: str):
    import requests
    import random
    import string
    import json

    token = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
    data.update({'wikidot_token7': token})
    cookies = requests.cookies.RequestsCookieJar()
    cookies.set('wikidot_token7', str(token), domain=wikidot_site + '.wikidot.com', path='/')
    p = requests.post('http://' + wikidot_site + '.wikidot.com/ajax-module-connector.php', data=data, cookies=cookies)
    response = json.loads(p.text)
    if response['status'] == 'ok':
        return response['body']

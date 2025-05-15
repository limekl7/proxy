import socket
import re # для получения кода ответа
import threading

BLOCKED_HOSTS = [

]

def log_request(url, status_code):
    if status_code == 'Unknown':
        return
    else:
        print(f"{url}, Код ответа: {status_code}")


def parse_request(data):
    try:
        if not data:
            return None, None, None, None
        lines = data.decode('utf-8', errors='ignore').split('\r\n')
        request_line = lines[0]
        method, path, protocol = request_line.split(' ')

        # получаем host
        host = ''
        for line in lines[1:]:
            if line.lower().startswith('host:'):
                host = line.split(' ')[1].strip()
                break


        if path.startswith('http://'):
            url = path
        else:
            url = f'http://{host}{path}'

        return method, url, host, protocol, data
    except:
        return None, None, None, None


def handle_client(client_socket):
    try:
        request_data = client_socket.recv(4096)

        method, url, host, protocol, request_data = parse_request(request_data)
        if not method or not host:
            return

        host_name = host.split(':')[0]
        if host_name in BLOCKED_HOSTS:
            return

        # получаем хост и порт
        host_parts = host.split(':')
        hostname = host_parts[0]
        port = int(host_parts[1]) if len(host_parts) > 1 else 80

        request_lines = request_data.decode('utf-8', errors='ignore').split('\r\n')
        if request_lines:
            path = url[len('http://' + host):]
            if not path:
                path = '/'
            request_lines[0] = f"{method} {path} {protocol}"
            modified_request = '\r\n'.join(request_lines).encode('utf-8')

        # соединение с сервером
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((hostname, port))
        server_socket.send(modified_request)

        response = b''
        headers_found = False
        max_header_size = 4096
        while True:
            try:
                data = server_socket.recv(4096)
                if not data:
                    break
                response += data
                client_socket.send(data)

                if not headers_found:
                    try:
                        response_str = response.decode('utf-8', errors='ignore')
                        if 'http' in response_str.lower():
                            headers_found = True
                            status_match = re.search(r'HTTP/\d\.\d\s+(\d+\s+[^\r\n]*)', response_str)
                            if status_match:
                                status = status_match.group(1)
                                log_request(url, status)
                            else:
                                status = 'Unknown'
                                log_request(url, status)
                    except Exception as e:
                        pass


                if len(response) > max_header_size:
                    status = 'Unknown'
                    log_request(url, status)
                    headers_found = True

            except Exception as e:
                break

    except Exception as e:
        pass
    finally:
        try:
            client_socket.close()
        except:
            pass
        try:
            server_socket.close()
        except:
            pass


def main():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind(('127.0.0.1', 5000))
    proxy_socket.listen(5)

    print("Прокси-сервер запущен на порту 5000")

    while True:
        try:
            client_socket, addr = proxy_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
            client_thread.start()

        except KeyboardInterrupt:
            proxy_socket.close()
            break
        except Exception as e:
            print(f"{str(e)}")


if __name__ == '__main__':
    main()
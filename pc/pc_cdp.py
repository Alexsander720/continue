"""Read-only CDP diagnostic helper. Uses stdlib ws_min, no Python packages."""
import json
import sys
import urllib.request

import ws_min as websocket

BASE = 'http://127.0.0.1:8080'


def targets():
    with urllib.request.urlopen(BASE + '/json', timeout=5) as response:
        return json.loads(response.read(2 * 1024 * 1024))


def call(sub, method, params=None, timeout=20):
    target = next(t for t in targets() if sub.lower() in t.get('title', '').lower())
    ws = websocket.create_connection(target['webSocketDebuggerUrl'], timeout=timeout, suppress_origin=True)
    try:
        ws.send(json.dumps({'id': 1, 'method': method, 'params': params or {}}))
        while True:
            result = json.loads(ws.recv())
            if result.get('id') == 1:
                return result
    finally:
        ws.close()


if __name__ == '__main__':
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 1 or sys.argv[1] == 'targets':
        print(json.dumps(targets(), ensure_ascii=False, indent=2))
    elif sys.argv[1] == 'eval':
        print(json.dumps(call(sys.argv[2], 'Runtime.evaluate', {'expression': sys.argv[3], 'returnByValue': True}), ensure_ascii=False))

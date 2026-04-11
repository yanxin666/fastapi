import http.client
import time

for i in range(10):
    try:
        conn = http.client.HTTPConnection('127.0.0.1', 8000, timeout=2)
        conn.request('GET', '/')
        r = conn.getresponse()
        print('status', r.status)
        print(r.read(1000).decode('utf-8', 'ignore'))
        break
    except Exception as e:
        print('try', i, 'failed', e)
        time.sleep(1)
else:
    print('server did not respond')

Partial replacement for stunnel
=================================

I couldn't make LibreSSL and stunnel play nice using the BSD ports system. Instead of playing "hunt down the incomplete/missing functions", let's implement what I wanted.

A localhost bonded unencrypted tunnel to communicate to another localhost TLS encrypted port.

Example
---------

On one console::

    (cpython36) terranova:~/software/pystunnel [master]$ python -m pystunnel 9678 443 yahoo.com
    [2017-04-16 20:21:02,355] [pystunnel.ProxiedClientConnection.unallocated-address-4491564256] [INFO] Created connection on behalf of 127.0.0.1:57087
    [2017-04-16 20:21:03,148] [pystunnel.RemoteTLSConnection.unallocated-address-4491563640] [INFO] Created connection on behalf of 98.138.253.109:443
    [2017-04-16 20:21:03,327] [pystunnel.ProxiedClientConnection.127-0-0-1_of_57087] [INFO] has closed normally
    [2017-04-16 20:21:15,357] [pystunnel.RemoteTLSConnection.98-138-253-109_of_443] [INFO] has closed normally

On the other::

    (cpython27) terranova:~/software/pystunnel [master]$ curl -Lv http://127.0.0.1:9678/
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 9678 (#0)
    > GET / HTTP/1.1
    > Host: 127.0.0.1:9678
    > User-Agent: curl/7.51.0
    > Accept: */*
    >
    < HTTP/1.1 404 Not Found on Accelerator
    < Date: Mon, 17 Apr 2017 03:21:03 GMT
    < Connection: keep-alive
    < Via: https/1.1 ir17.fp.ne1.yahoo.com (ApacheTrafficServer)
    < Server: ATS
    < Cache-Control: no-store
    < Content-Type: text/html
    < Content-Language: en
    < Content-Length: 6502
    <
    <!DOCTYPE html>
    ...


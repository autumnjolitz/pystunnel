Partial replacement for stunnel
=================================

I couldn't make LibreSSL and stunnel play nice using the BSD ports system. Instead of playing "hunt down the incomplete/missing functions", let's implement what I wanted.

Provides:

* A localhost bonded unencrypted tunnel to communicate to another TLS encrypted port.
* A localhost bonded encrypted tunnel to another unencrypted port.


Example (SSL Stripping)
-------------------------

On one console::

    (cpython36) terranova:~/software/pystunnel [master]$ python -m pystunnel strip 9678 443 yahoo.com
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

Example SSL Wrapping
----------------------

I'll be using a certificate of my own. Obviously you'll have to provide your own.

Start the tunnel::

    (cpython36) terranova:~/software/pystunnel [master]$ python -m pystunnel wrap -c tls.crt -k tls.key localhost 8443 8080 localhost
    [2017-08-05 18:20:57,251] [pystunnel.ProxiedClientConnection.unallocated-address-4410813128] [INFO] Created connection on behalf of 127.0.0.1:49473
    [2017-08-05 18:20:57,256] [pystunnel.RemoteTLSConnection.unallocated-address-4410812904] [INFO] Created connection on behalf of 127.0.0.1:8080
    [2017-08-05 18:20:57,257] [pystunnel.RemoteTLSConnection.127-0-0-1_of_8080] [INFO] has closed normally
    [2017-08-05 18:20:57,257] [pystunnel.ProxiedClientConnection.127-0-0-1_of_49473] [INFO] has closed normally


Create the Test HTTP Server::

    (cpython36) terranova:~/test$ python -m http.server 8080
    Serving HTTP on 0.0.0.0 port 8080 (http://0.0.0.0:8080/) ...
    127.0.0.1 - - [05/Aug/2017 18:20:57] "GET / HTTP/1.1" 200 -


Prove TLS wrapping::

    (cpython27) terranova:~$ curl -Lv --resolve subdomain.telemuse.net:8443:127.0.0.1 https://subdomain.telemuse.net:8443
    * Added subdomain.telemuse.net:8443:127.0.0.1 to DNS cache
    * Rebuilt URL to: https://subdomain.telemuse.net:8443/
    * Hostname subdomain.telemuse.net was found in DNS cache
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to subdomain.telemuse.net (127.0.0.1) port 8443 (#0)
    * TLS 1.2 connection using TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    * Server certificate: *.telemuse.net
    * Server certificate: COMODO RSA Domain Validation Secure Server CA
    * Server certificate: COMODO RSA Certification Authority
    > GET / HTTP/1.1
    > Host: subdomain.telemuse.net:8443
    > User-Agent: curl/7.51.0
    > Accept: */*
    >
    * HTTP 1.0, assume close after body
    < HTTP/1.0 200 OK
    < Server: SimpleHTTP/0.6 Python/3.6.0
    < Date: Sun, 06 Aug 2017 01:20:57 GMT
    < Content-type: text/html; charset=utf-8
    < Content-Length: 340
    <
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    ...


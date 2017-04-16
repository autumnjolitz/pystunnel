Partial replacement for stunnel
=================================

I couldn't make LibreSSL and stunnel play nice using the BSD ports system. Instead of playing "hunt down the incomplete/missing functions", let's implement what I wanted.

A localhost bonded unencrypted tunnel to communicate to another localhost TLS encrypted port.
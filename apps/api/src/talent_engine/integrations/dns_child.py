"""Bounded DNS resolution without inherited credentials."""

import json
import resource
import socket
import sys

resource.setrlimit(resource.RLIMIT_AS, (134217728, 134217728))
resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
try:
    addresses = sorted(
        {
            (r[4][0], r[0])
            for r in socket.getaddrinfo(
                sys.argv[1], int(sys.argv[2]), type=socket.SOCK_STREAM
            )
        }
    )
    if not addresses or len(addresses) > 32:
        raise ValueError("Address limit")
    print(json.dumps(addresses))
except Exception:
    sys.exit(1)

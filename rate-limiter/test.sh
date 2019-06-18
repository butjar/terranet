curl -X PUT 10.0.0.1:5000/limit/h1-eth0/ -H "Content-Type: application/json" -d '{"rate": "1mbit", "burst": "32kbit", "latency": "10ms"}'

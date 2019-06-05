# Microservice Simulation

ms-sim is a toolbox designed to build simulated microservices running on real hardware. MS-Sim services utilize real system resources and rely on an underlying physical or virtual network. 

## MS-Sim Component Diagram

![alt text](https://raw.githubusercontent.com/mwallschlaeger/MS-Sim/master/docs/MS-SIM-single-service-diagram.pn)

This diagram describes the components and features of MS-Sim.
You can combine those features using the yaml definition language. Examples can be found in the yaml-definitions folder.

## MS-Sim Service Interaction Diagram
![alt text](https://raw.githubusercontent.com/mwallschlaeger/MS-Sim/master/docs/MS-SIM-microservice-architecture-example.png)

## How to Start:

Clone:
git clone --recurse-submodules https://gitlab.tubit.tu-berlin.de/tibut/MS-Sim.git

### Start Example Services:

Start example Compute Service (Noops) 
```
./ms-yaml-build.py -y yaml-definitions/test-compute.yaml -p
```

Start example proxy (Forwarder)
The proxy forwards received packets to compute and from compute service back to the requester
```
./ms-yaml-build.py -y yaml-definitions/test-proxy.yaml
```

### Packet Generator:
Packet generator simulates IoT devices sending data to the proxy service
``` 
./ms-device-simulator.py -devices 500 -host localhost:5090
```

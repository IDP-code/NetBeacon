# NetBeacon
[An Efficient Design of Intelligent Network Data Plane](https://www.usenix.org/conference/usenixsecurity23/presentation/zhouguangmeng)  USENIX Security 2023

#### model_generation
train and transform models to flow tables

#### switch
the codes running in switch including control plane and data plane


#### Excute
##### Generate flow table
1. python model_representation.py
##### Excute Traffic classification
1. complie and run p4 code (switch.p4) of data plane, and set switch port
2. run the code (controller.py ) of control plane 
3. send traffic...

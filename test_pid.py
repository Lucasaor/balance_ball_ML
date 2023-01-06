from pid import PID
import time

def proportional(Kp, SP):
    """Creates proportional controllers with specified gain and setpoint."""
    MV = 0
    while True:
        PV = yield MV
        MV = Kp * (SP - PV)

controller1 = proportional(10, 40)
controller1.send(None)

controller2 = proportional(1, 40)
controller2.send(None)

PV = 35

print("Controller 1: MV = ", controller1.send(PV))
print("Controller 2: MV = ", controller2.send(PV))

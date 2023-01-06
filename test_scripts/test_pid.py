from pid import PID
import time

def texter_gen():
    a = yield "Started"
    b = yield a
    yield b

texter = texter_gen()
print(texter.send(None))
print(texter.send("Hello, World"))
print(texter.send("Go Bulls!"))
print(texter.send("bolsonaro nunca mais!"))
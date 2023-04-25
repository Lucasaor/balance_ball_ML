from opcua import Client

def main():
    client = Client('opc.tcp://192.168.137.1:49320',timeout=360)
    client.set_user("datauser")
    client.set_password("qwertyuiop1234567890")
    client.connect()
    print("OK")
    client.disconnect()


if __name__ == '__main__':
     main()
     
     
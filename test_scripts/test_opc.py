from asyncua import Client,ua
import asyncio


async def main():
    client = Client(url='opc.tcp://192.168.137.1:49320')
    client.set_user("datauser")
    client.set_password("qwertyuiop1234567890")
    async with client:
        # Do something with client
        pos = 10
        if servo == 1:
            node = client.get_node('ns=2;s=Channel1.Device1.BracoA')
        else:
            node = client.get_node('ns=2;s=Channel1.Device1.BracoB')
        await node.set_value(ua.DataValue(ua.Variant(pos/10, ua.VariantType.Float)))
            
        
        pos = -10        
        node = client.get_node('ns=2;s=Channel1.Device1.BracoB')
        await node.set_value(ua.DataValue(ua.Variant(pos/10, ua.VariantType.Float)))
        print("node 2 ok")
        

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
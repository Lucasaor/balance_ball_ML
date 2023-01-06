import json
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData

async def publish_event(dict_data:dict):
    # Create a producer client to send messages to the event hub.
    # Specify a connection string to your event hubs namespace and
    # the event hub name.
    with open("conn_str.json","rb") as fp:
        conn_data = json.load(fp)
    producer = EventHubProducerClient.from_connection_string(conn_str=conn_data['conn_str'], eventhub_name=conn_data["eventhub_name"])
    async with producer:
        # Create a batch.
        event_data_batch = await producer.create_batch()
        table_data = json.dumps(dict_data)
        # Add events to the batch.
        event_data_batch.add(EventData(table_data))
        # Send the batch of events to the event hub.
        await producer.send_batch(event_data_batch)


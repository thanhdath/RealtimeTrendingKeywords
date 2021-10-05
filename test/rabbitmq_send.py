import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='articles')

channel.basic_publish(exchange='',
                      routing_key='articles',
                      body='Hello Worldxzzzzzzzzzzzzzz !')
print(" [x] Sent 'Hello World!'")

connection.close()

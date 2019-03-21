import pika
import re


connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', port=5672))
channel = connection.channel()

channel.exchange_declare(exchange='to_server',
                         exchange_type='topic')

channel.exchange_declare(exchange='to_client',
                         exchange_type='topic')

# создание эксклюзивной очереди и подписка на заданные exchange, rout_key, func
def new_consume(callback_func, exchange, routing_key):
    global channel
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=exchange, queue=queue_name,
                       routing_key=routing_key)
    channel.basic_consume(callback_func, queue=queue_name,
                          no_ack=True)



listUsers = []
def find_user(login):
    login = login.lower()
    for user in listUsers:
        if user.lower() == login:
            return True
    return False
# прием сообщений авторизации
def Auth_callback(ch, method, props, body):
    login = body.decode('utf-8')
    result = re.match(r'[a-zA-Zа-яА-Я0-9!№;%:?*()@#$^&\[\]]{1,32}', login)
    if (result != None) and (result.group(0) == login) and not find_user(login):
        listUsers.append(login)
        channel.basic_publish(exchange='',
                              routing_key=props.reply_to,
                              body='True')
    else:
        channel.basic_publish(exchange='',
                              routing_key=props.reply_to,
                              body='False')

# прием приватных сообщений
def PrivateMsg_callback(ch, method, props, body):
    print('headers: ', props.headers)
    print('server: pm: ', body.decode('utf-8'))

# прием сообщений общего чата
def CommonMsg_callback(ch, method, props, body):
    #print(props.headers)
    channel.basic_publish(exchange='to_client', routing_key='msg.common',
                          body=body, properties=props)

# запросы на обновление списка онлайн
def refreshOnlineList_callback(ch, method, props, body):
    users_str = ''
    if len(listUsers) > 0:
        for i in range(len(listUsers) - 1):
            users_str += listUsers[i] + '|'
        users_str += listUsers[len(listUsers) - 1]
    channel.basic_publish(exchange='to_client', routing_key='online_users',
                          body=users_str)

# сообщения отключения от сервера
def logout_callback(ch, method, props, body):
    if listUsers.count(body.decode('utf-8')) > 0:
        listUsers.remove(body.decode('utf-8'))
    refreshOnlineList_callback(ch, method, props, body)

new_consume(Auth_callback, 'to_server', 'auth')
new_consume(PrivateMsg_callback, 'to_server', 'msg.private')
new_consume(CommonMsg_callback, 'to_server', 'msg.common')
new_consume(refreshOnlineList_callback, 'to_server', 'get_online_users')
new_consume(logout_callback, 'to_server', 'logout')


#:pika.BasicProperties





channel.start_consuming()
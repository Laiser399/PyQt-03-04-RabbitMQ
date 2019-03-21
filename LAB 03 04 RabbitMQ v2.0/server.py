import pika
import re


# создание эксклюзивной очереди и подписка на заданные exchange, rout_key, func
def new_consume(callback_func, exchange, routing_key):
    global channel
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=exchange, queue=queue_name,
                       routing_key=routing_key)
    channel.basic_consume(callback_func, queue=queue_name,
                          no_ack=True)

# словарь (имя_пользователя - название_его_очереди)
listUsers = {}
def find_user(login):
    login = login.lower()
    keys = listUsers.keys()
    for key in keys:
        key = key.lower()
        if key == login:
            return True
    return False

# прием сообщений авторизации возвращает созданную очередь
def Auth_callback(ch, method, props, body):
    login = body.decode('utf-8')
    result = re.match(r'[a-zA-Zа-яА-Я0-9!№;%:?*()@#$^&\[\]]{1,32}', login)
    if (result != None) and (result.group(0) == login) and not find_user(login):
        # создание эксклюзивной очереди
        res = channel.queue_declare(exclusive=True)
        queue_name = res.method.queue
        channel.queue_bind(exchange='to_client', queue=queue_name,
                           routing_key='msg.common')

        listUsers[login] = queue_name
        channel.basic_publish(exchange='',
                              routing_key=props.reply_to,
                              body=queue_name)
    else:
        channel.basic_publish(exchange='',
                              routing_key=props.reply_to,
                              body='')

# TODO
# прием сообщений от пользователей и распределение по очередям
def message_callback(ch, method, props, body):
    # получение инфо об отправителе и получателе
    sender = props.headers.get('sender')
    receiver = props.headers.get('receiver')

    if receiver == None:
        # common msgs TODO
        pass
    else:
        # pm msgs
        if sender == None:
            return


# запросы на обновление списка онлайн
def refreshOnlineList_callback(ch, method, props, body):
    users_str = ''
    if len(listUsers) > 0:
        for user in listUsers:
            users_str += user + '|'
        users_str = users_str[:-1]
    channel.basic_publish(exchange='to_client', routing_key='online_users',
                          body=users_str)

# сообщения отключения от сервера
def logout_callback(ch, method, props, body):
    listUsers.pop(body.decode('utf-8'), None)
    refreshOnlineList_callback(ch, method, props, body)


#:pika.BasicProperties

# DEBUG
if False:
    dict1 = {'123': 22,
             'sad' : 1}
    dict1['dfgyhj'] = 123
    print(dict1.get(123))

    print(dict1.keys())

if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=5672))
    channel = connection.channel()

    channel.exchange_declare(exchange='to_server',
                             exchange_type='topic')

    channel.exchange_declare(exchange='to_client',
                             exchange_type='topic')

    new_consume(Auth_callback, 'to_server', 'auth')
    new_consume(message_callback, 'to_server', 'msg')
    new_consume(refreshOnlineList_callback, 'to_server', 'get_online_users')
    new_consume(logout_callback, 'to_server', 'logout')

    channel.start_consuming()










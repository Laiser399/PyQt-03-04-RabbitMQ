import pika
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, \
    QTabWidget, QLineEdit, QListWidget, QSplitter, QListWidgetItem, \
    QMessageBox, QTextEdit
from PyQt5.QtCore import QThread, QModelIndex, pyqtSignal
from LoginDlg import LoginDlg
from datetime import datetime

# class consumingThread(QThread):
#     def __init__(self, callback, exchange, routing_key, parent=None):
#         QThread.__init__(self, parent)
#         self.callback = callback
#         self.exchange = exchange
#         self.routing_key = routing_key
#
#     def run(self):
#         self.connection = pika.BlockingConnection(pika.ConnectionParameters(
#             host='localhost', port=5672))
#         self.channel = self.connection.channel()
#
#         result = self.channel.queue_declare(exclusive=True)
#         queue = result.method.queue
#         self.channel.queue_bind(exchange=self.exchange, queue=queue,
#                                 routing_key=self.routing_key)
#         self.channel.basic_consume(self.callback, queue=queue,
#                                    no_ack=True)
#         print('exchange: ', self.exchange)
#         print('routing_key: ', self.routing_key)
#         print('callback: ', self.callback)
#         print('queue: ', queue)
#         print()
#
#         self.channel.start_consuming()
#
#     def __del__(self):
#         pass

class consumingThread(QThread):
    def __init__(self, callback, exchange, routing_key, parent=None):
        QThread.__init__(self, parent)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=5672))
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.queue = result.method.queue
        self.channel.queue_bind(exchange=exchange, queue=self.queue,
                                routing_key=routing_key)
        self.channel.basic_consume(callback, queue=self.queue,
                                   no_ack=True)

    def run(self):
        self.channel.start_consuming()

    def __del__(self):
        self.channel.queue_delete(queue=self.queue)
        self.connection.close()

class ClientWindow(QMainWindow):
    TabChats = None
    LoginEdit = None

    nickname = None
    queue_name = None

    opened_pm = [] # список пользователей для который открыты вкладки ЛС
    pm_signal = pyqtSignal(str, str)
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle('Чат')
        self.setWidgets()
        self.pm_signal.connect(self.slot_privateMessage)

        self.resize(500, 400)

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=5672))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='to_server',
                                 exchange_type='topic')

        self.channel.exchange_declare(exchange='to_client',
                                 exchange_type='topic')


        # диалог ввода логина, запрос на обновление онлайн пользователей
        dlg = LoginDlg()
        resAuth = dlg.getAuthInfo()
        if resAuth == None:
            exit()
        self.nickname = resAuth[0]
        self.queue_name = resAuth[1]
        self.LoginEdit.setText(self.nickname)

        # подписки
        self.commonChatThread = consumingThread(self.callback_commonMessages,
                                                'to_client', 'msg.common')
        self.privateChatThread = consumingThread(self.callback_privateMessages,
                                                 'to_client', 'msg.private.*.' + self.nickname)
        self.refreshOnlineThread = consumingThread(self.callback_onlineUsers,
                                                   'to_client', 'online_users')
        self.commonChatThread.start()
        self.privateChatThread.start()
        self.refreshOnlineThread.start()

        self.channel.basic_publish(exchange='to_server', routing_key='get_online_users',
                                   body='')

    def setWidgets(self):
        '''расстановка виджетов'''
        splitter = QSplitter()

        w_chat = QWidget()
        chatLay = QVBoxLayout()
        self.TabChats = QTabWidget()
        inputEdit = QLineEdit()
        chatLay.addWidget(self.TabChats)
        chatLay.addWidget(inputEdit)
        w_chat.setLayout(chatLay)

        w_online = QWidget()
        onlineLay = QVBoxLayout()
        self.LoginEdit = QLineEdit()
        self.LoginEdit.setReadOnly(True)
        self.onlineList = QListWidget()
        onlineLay.addWidget(self.LoginEdit)
        onlineLay.addWidget(self.onlineList)
        w_online.setLayout(onlineLay)

        splitter.addWidget(w_chat)
        splitter.addWidget(w_online)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        # добавление оьщего чата
        textEdit = QTextEdit()
        textEdit.setReadOnly(True)
        self.TabChats.addTab(textEdit, 'Общий чат')


        # коннект нажатия ввода на edit
        inputEdit.returnPressed.connect(self.slot_sendMessage)
        # коннект двойного клика по пользователю
        self.onlineList.doubleClicked.connect(self.slot_DClickUser)

    def closeEvent(self, *args, **kwargs):
        # сообщение отключения от сервера
        self.channel.basic_publish(exchange='to_server', routing_key='logout',
                                   body=self.nickname)

    def callback_commonMessages(self, ch, method, props, body):
        if props.headers.get('sender') == None:
            return

        time = datetime.strftime(datetime.now(), "[%H:%M:%S]")
        common_edit = self.TabChats.widget(0)
        common_edit.append('<b>' + time + ' ' + props.headers.get('sender') + ': </b>' + body.decode('utf-8'))

        #print()
        # scroll = common_edit.verticalScrollBar()
        # scroll.setTracking(False)
        # while scroll.value() != scroll.maximum():
        #     scroll.setValue(scroll.maximum())

        #scroll.setSliderPosition( + 100)

    def slot_privateMessage(self, sender, msg):
        '''слот вызывается при приеме приватного сообщения
        (при созданни вкладки из ф-ии callback были баги с tabwidget)'''
        index = None
        for i in range(len(self.opened_pm)):
            if self.opened_pm[i] == sender:
                index = i + 1
                break

        if index == None:
            textEdit = QTextEdit()
            textEdit.setReadOnly(True)
            self.TabChats.addTab(textEdit, sender)

            self.opened_pm.append(sender)
            index = self.TabChats.count() - 1
        time = datetime.strftime(datetime.now(), "[%H:%M:%S]")
        currEdit = self.TabChats.widget(index)
        currEdit.append('<b>' + time + ' ' + sender + ': </b>' + msg)

    def callback_privateMessages(self, ch, method, props, body):
        sender = props.headers.get('sender')
        if sender == None:
            return
        self.pm_signal.emit(sender, body.decode('utf-8'))

    def callback_onlineUsers(self, ch, method, props, body):
        '''получение списка онлайн пользователей от сервера'''
        usersStr = body.decode('utf-8')
        users = usersStr.split('|')
        self.onlineList.clear()
        for user in users:
            item = QListWidgetItem(user)
            self.onlineList.addItem(item)

    def slot_sendMessage(self):
        '''отправка сообщения (enter)'''
        # .lstrip()
        if len(self.sender().text()) == 0:
            return
        if self.TabChats.currentIndex() == 0:
            self.channel.basic_publish(exchange='to_server', routing_key='msg',
                                       body=self.sender().text(),
                                       properties=pika.BasicProperties(
                                          headers={'sender' : self.nickname}
                                       ))

        else:
            receiver_nick = self.TabChats.tabText(self.TabChats.currentIndex())
            self.channel.basic_publish(exchange='to_server', routing_key='msg',
                                       body=self.sender().text(),
                                       properties=pika.BasicProperties(
                                           headers={'sender' : self.nickname,
                                                    'receiver' : receiver_nick}
                                       ))
            time = datetime.strftime(datetime.now(), '[%H:%M:%S]')
            self.TabChats.widget(self.TabChats.currentIndex()).\
                append('<b>' + time + ' ' + self.nickname + ': </b>' + self.sender().text())
        self.sender().setText('')

    def slot_DClickUser(self, index: QModelIndex):
        '''двойной клик по полбзователю из списка онлайн'''
        if (index.data() == self.nickname) or (self.opened_pm.count(index.data()) != 0):
            return
        new_text_edit = QTextEdit()
        new_text_edit.setReadOnly(True)
        self.TabChats.addTab(new_text_edit, index.data())
        self.opened_pm.append(index.data())

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    wnd = ClientWindow()
    wnd.show()

    sys.exit(app.exec_())
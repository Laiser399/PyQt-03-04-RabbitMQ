import pika
from PyQt5.QtWidgets import QDialog, QGridLayout, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt, QThread



# thread создает уникальную очередь, подписывается на нее, callback-функция передается в конструктор
class responseThread(QThread):
    queue_name = None
    callback = None
    channel = None
    def __init__(self, callback_func, parent=None):
        QThread.__init__(self, parent)
        self.callback = callback_func

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=5672))
        self.channel = self.connection.channel()
        queue_login_response = self.channel.queue_declare(exclusive=True)
        self.queue_name = queue_login_response.method.queue

        self.channel.basic_consume(self.callback,
                                   queue=self.queue_name,
                                   no_ack=True)

    def run(self):
        self.channel.start_consuming()

# диалог получения логина
class DlgInputLogin(QDialog):
    ok = False
    bPressed = False
    edit = None
    response = None
    currLogin = None
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWidgets()

    def setWidgets(self):
        self.setWindowTitle('Авторизация')
        self.resize(260, 100)

        lay = QGridLayout()

        self.edit = QLineEdit()
        bEnter = QPushButton('Войти')
        bEnter.setMaximumWidth(120)
        bEnter.clicked.connect(self.slot_enterPressed)

        lay.addWidget(QLabel('Логин:'), 0, 0, Qt.AlignRight)
        lay.addWidget(self.edit, 0, 1, 1, 2)
        lay.addWidget(bEnter, 1, 0, 1, 3, Qt.AlignHCenter)

        lay.setColumnStretch(1, 1)

        self.setLayout(lay)

    def showEvent(self, QShowEvent):
        self.ok = False
        self.bPressed = False

    def callback(self, ch, method, props, body):
        self.response = None
        self.bPressed = False
        if (body.decode('utf-8') == 'True'):
            self.ok = True
            self.close()
        else:
            print('false')

    def slot_enterPressed(self):
        if self.bPressed:
            return
        self.bPressed = True
        self.currLogin = self.edit.text()

        self.response = responseThread(self.callback)
        queue_name = self.response.queue_name

        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=5672))
        channel = connection.channel()
        channel.exchange_declare(exchange='to_server',
                                 exchange_type='topic')
        channel.basic_publish(exchange='to_server',
                              routing_key='auth',
                              properties=pika.BasicProperties(reply_to=queue_name),
                              body=self.currLogin)
        connection.close()
        self.response.start()

    def getNickname(self):
        self.exec()
        if (self.ok):
            return self.currLogin
        else:
            return None


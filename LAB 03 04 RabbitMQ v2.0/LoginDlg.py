import pika
from PyQt5.QtWidgets import QDialog, QGridLayout, QLineEdit, QPushButton, \
    QLabel, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QThread, QTimer

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

    def __del__(self):
        self.channel.queue_delete(queue=self.queue_name)
        self.connection.close()

# диалог получения логина
class LoginDlg(QDialog):
    ok = False
    bPressed = False
    edit = None
    response = None
    currLogin = None
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWidgets()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.slot_time_is_out)

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
        '''вызывается при поступлении ответа от сервера'''
        self.timer.stop()
        self.response = None
        self.bPressed = False
        if (len(body.decode('utf-8')) == 0):
            print('nickname is not available')
        else:
            self.ok = True
            self.queue_name = body.decode('utf-8')
            self.close()

    def slot_enterPressed(self):
        '''нажате кнопки Войти'''
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

        self.timer.start(3000) # таймер ожидания ответа сервера

    def slot_time_is_out(self):
        '''ответ от сервера не получен за определенное время'''
        QMessageBox.information(None, 'Внимание', 'Время ожидания сервера вышло!')
        self.bPressed = False
        self.response = None


    def getAuthInfo(self):
        '''получение логина из диалога'''
        self.exec()
        if (self.ok):
            return [self.currLogin, self.queue_name]
        else:
            return None

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    dlg = LoginDlg()
    print('nickname: ', dlg.getAuthInfo())
    dlg = None
    #app.exec()
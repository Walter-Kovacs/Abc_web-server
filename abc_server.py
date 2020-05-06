import csv
import io
import json
import os.path
import shutil

from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

__version__ = "0.0"


class AbcHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "AbcHTTP/" + __version__
    protocol_version = "HTTP/1.1"

    pages_path = "www"
    main_page_path = os.path.join(pages_path, "MainPage.html")
    user_accounts_page_path = os.path.join(pages_path, "UserAccountsPage.html")
    user_accounts_page_above_rows = None
    user_account_row_template = None
    user_accounts_page_below_rows = None

    request_user_login = "/user/?login="

    # noinspection PyPep8Naming
    def do_HEAD(self):
        self.send_response(HTTPStatus.NOT_IMPLEMENTED)

    # noinspection PyPep8Naming
    def do_GET(self):
        request = self.path
        print(request)
        # Main page
        if request == "/":
            self.send_main_page()
        # User sign in
        elif request.startswith(self.request_user_login):
            self.send_user_accounts(request[len(self.request_user_login):])
        # 404
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    # noinspection PyPep8Naming
    def do_POST(self):
        request = self.path
        print(request)
        # read request body
        content_length = 0
        h = self.headers
        for item in h.items():
            if item[0].lower() == "content-length":
                content_length = int(item[1])
                break
        if content_length != 0:
            request_body = self.rfile.read(content_length).decode('utf-8')
        else:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        print(request_body)

        # request_body: param=value&param=value&parm=value
        param_dict = {}
        for param in request_body.split('&'):
            key_and_value = param.split('=')
            param_dict[key_and_value[0]] = key_and_value[1]
        
        # action with account
        if request == "/user/accounts/action":
            # request_body: login=user1&account-number=001&amount=100&account-action=deposit
            dbh = UserDatabaseHandler(param_dict["login"])
            result_of_request_to_db = dbh.action_on_account(param_dict)
        # create new account
        elif request == "/user/accounts/create":
            # request_body: login=user1&currency=RUB
            dbh = UserDatabaseHandler(param_dict["login"])
            result_of_request_to_db = dbh.create_new_account(param_dict)
        # 404
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        # send result
        if result_of_request_to_db == UserDatabaseHandler.REQUEST_RESULT_OK:
            self.send_user_accounts(param_dict["login"])
        else:
            self.send_user_accounts_error_page(result_of_request_to_db)

    def send_main_page(self):
        with open(self.main_page_path, 'rb') as main_page:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=UTF-8")
            self.send_header("Content-Length", str(os.fstat(main_page.fileno())[6]))
            self.end_headers()
            shutil.copyfileobj(main_page, self.wfile)

    def __init_user_accounts_template__(self):
        with open(self.user_accounts_page_path, 'r') as f:
            start_mark = "{begin account-row-template}"
            end_mark = "{end account-row-template}"
            page_template = f.read()
            self.user_accounts_page_above_rows = page_template[:page_template.find(start_mark)]
            self.user_account_row_template = \
                page_template[page_template.find(start_mark) + len(start_mark):page_template.find(end_mark)]
            self.user_accounts_page_below_rows = page_template[page_template.find(end_mark) + len(end_mark):]

    def send_user_accounts(self, username):
        dbh = UserDatabaseHandler(username)
        user_accounts = dbh.get_user_accounts('r')
        if user_accounts is not None:
            if self.user_accounts_page_above_rows is None:
                self.__init_user_accounts_template__()

            accounts_rows = ""
            accounts_dict = json.load(user_accounts)
            user_accounts.close()
            for account_number in accounts_dict:
                a_row = self.user_account_row_template.\
                    replace("{number}", account_number).\
                    replace("{currency}", accounts_dict[account_number]["currency"]).\
                    replace("{amount}", str(accounts_dict[account_number]["amount"])).\
                    replace("{username}", username)
                accounts_rows += a_row + '\n'

            response_body = \
                self.user_accounts_page_above_rows.replace("{username}", username) \
                + accounts_rows \
                + self.user_accounts_page_below_rows
            response_body = response_body.encode('utf-8')
            response_body_stream = io.BytesIO()
            response_body_stream.write(response_body)
            response_body_stream.seek(0)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=UTF-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            shutil.copyfileobj(response_body_stream, self.wfile)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)  # TODO: create account

    def send_user_accounts_error_page(self, result_of_request_to_db):
        # TODO: replace sending INTERNAL_SERVER_ERROR of creating html page and send it
        self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, message=result_of_request_to_db)


# TODO:
#  py file for class
#  request result constants outside the class
class UserDatabaseHandler:
    database_path = "database"
    index = os.path.join(database_path, "database.index")

    REQUEST_RESULT_OK = 0
    REQUEST_RESULT_ERROR_WRONG_REQUEST_OR_DATABASE_ERROR = 100
    REQUEST_RESULT_ERROR_WRONG_REQUEST = 200
    REQUEST_RESULT_ERROR_WRONG_REQUEST_INSUFFICIENT_FUNDS = 201
    REQUEST_RESULT_ERROR_WRONG_REQUEST_UNSUPPORTED_ACTION = 202
    REQUEST_RESULT_ERROR_DATABASE_ERROR = 300

    def __init__(self, username):
        self.username = username

    def get_user_accounts_path(self):
        """
        Search the path to the user accounts info file from database index file. Return path or None.
        :return: path or empty string
        """
        with open(self.index, 'r') as index_file:
            for row in csv.reader(index_file):
                if row[0] == self.username:
                    file_path = os.path.join(self.database_path, row[1])
                    break
        if os.path.isfile(file_path):
            return file_path
        else:
            return ""

    def get_user_accounts(self, mode):
        """
        Open file self.get_user_accounts_path and return corresponding file object.
        If self.get_user_accounts_path return None, this function return None too.
        :param mode: have the same meaning as in built-in function open()
        :return: file object or None
        """
        file_path = self.get_user_accounts_path()
        if file_path is not None:
            return open(file_path, mode)
        else:
            return None

    def create_new_account(self, param_dict):
        """
        Crete new account with currency param_dict['currency']
        :param param_dict: dictionary {'login': str, 'currency': str}
        :return: REQUEST_RESULT_* constant
        """
        if 'currency' not in param_dict:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST
        currency = param_dict['currency']

        accounts_file_path = self.get_user_accounts_path()
        if accounts_file_path == "":
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST_OR_DATABASE_ERROR
        with open(accounts_file_path, 'r') as file:
            accounts = json.load(file)

        acc_number_lst = []
        for acc in accounts:
            acc_number_lst.append(int(acc))
        acc_number_lst.sort()

        if len(acc_number_lst) != 0:
            new_account_number = acc_number_lst[-1] + 1
            if new_account_number > 999:
                return UserDatabaseHandler.REQUEST_RESULT_ERROR_DATABASE_ERROR
        else:
            new_account_number = 1

        accounts[str(new_account_number).rjust(3, '0')] = {'currency': currency, 'amount': 0.0}
        with open(accounts_file_path, 'w') as file:
            json.dump(accounts, file)
        return UserDatabaseHandler.REQUEST_RESULT_OK

    def action_on_account(self, param_dict):
        """
        Perform action param_dict['account-action'] (deposit/withdraw) on account
        witch number is param_dict['account-number'] and which belongs to the user param_dict['login']
        :param param_dict: dictionary {'login': str, 'account-number': str, 'amount': str, 'account-action': str}
        :return: REQUEST_RESULT_* constant
        """
        if 'account-number' not in param_dict:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST
        if 'account-action' not in param_dict:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST
        if 'amount' not in param_dict:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST

        number = param_dict['account-number']
        action = param_dict['account-action']
        amount_for_action = round(float(param_dict['amount']), 2)

        accounts_file_path = self.get_user_accounts_path()
        if accounts_file_path == "":
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST_OR_DATABASE_ERROR
        with open(accounts_file_path, 'r') as file:
            accounts = json.load(file)

        if number not in accounts:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_DATABASE_ERROR
        acc = accounts[number]
        if 'amount' not in acc:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_DATABASE_ERROR
        amount_in_account = acc['amount']

        if action == 'deposit':
            amount_in_account += amount_for_action
        elif action == 'withdraw':
            if amount_in_account >= amount_for_action:
                amount_in_account -= amount_for_action
            else:
                return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST_INSUFFICIENT_FUNDS
        else:
            return UserDatabaseHandler.REQUEST_RESULT_ERROR_WRONG_REQUEST_UNSUPPORTED_ACTION

        with open(accounts_file_path, 'w') as file:
            acc['amount'] = round(amount_in_account, 2)
            json.dump(accounts, file)
            return UserDatabaseHandler.REQUEST_RESULT_OK


def run(server_class=ThreadingHTTPServer, handler_class=AbcHTTPRequestHandler):
    server_address = ('localhost', 8080)
    httpd = server_class(server_address, handler_class)
    print("Python system version:", handler_class.sys_version)
    print("Server version:", handler_class.server_version)
    httpd.serve_forever()


if __name__ == "__main__":
    run()

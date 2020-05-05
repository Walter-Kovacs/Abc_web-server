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
        # action with account
        if request == "/user/accounts/action":
            content_length = 0
            h = self.headers
            for item in h.items():
                if item[0].lower() == "content-length":
                    content_length = int(item[1])
                    break
            if content_length != 0:
                request_of_action_string = self.rfile.read(content_length).decode('utf-8')
                print(request_of_action_string)  # TODO: CONTINUE 'login=user1&amount=100.1&account-action=deposit'
                self.send_error(HTTPStatus.NOT_IMPLEMENTED)  # TODO: delete
            else:
                self.send_error(HTTPStatus.BAD_REQUEST)
        # 404
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

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
        user_accounts = dbh.get_user_accounts()
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

            response_body = self.user_accounts_page_above_rows + accounts_rows + self.user_accounts_page_below_rows
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


class UserDatabaseHandler:
    database_path = "database"
    index = os.path.join(database_path, "database.index")

    def __init__(self, username):
        self.username = username

    def get_user_accounts(self):
        with open(self.index, 'r') as index_file:
            for row in csv.reader(index_file):
                if row[0] == self.username:
                    file_path = os.path.join(self.database_path, row[1])
                    break
        if os.path.isfile(file_path):
            return open(file_path, 'r')
        else:
            return None


def run(server_class=ThreadingHTTPServer, handler_class=AbcHTTPRequestHandler):
    server_address = ('localhost', 8080)
    httpd = server_class(server_address, handler_class)
    print("Python system version:", handler_class.sys_version)
    print("Server version:", handler_class.server_version)
    httpd.serve_forever()


if __name__ == "__main__":
    run()

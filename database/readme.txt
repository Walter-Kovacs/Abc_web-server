Database consists of index file 'database.index' and user accounts files '*.acc'
-------------------------------------------------------------------------------
File database.index is csv file like:
user1,user1.acc
user2,user2.acc

Each row in the file like: <user name>,<file.acc>
<user name> - user login,
<file.acc> - name of file in the database, which contain user accounts info
------------------------------------------------------------------------------
File *.acc is json file like:
{
  "001": {
    "currency": "RUB",
    "amount": 350.53
  },
  "account number": {
    "currency": "USD",
    "amount": 100.0
  }
}

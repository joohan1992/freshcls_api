import psycopg2


class DbConn:
    def __init__(self):
        self.db = psycopg2.connect(host='10.28.78.30', dbname='freshcls', user='postgres', password='ri1234!@', port=5432)
        self.cursor = self.db.cursor()

    def __del__(self):
        self.db.close()
        self.cursor.close()

    def execute(self, query, args=None):
        if args is None:
            args = {}
        self.cursor.execute(query, args)
        row = self.cursor.fetchall()
        return row

    def commit(self):
        self.cursor.commit()

    def insert(self, query, text=None):
        if text is None:
            text = 'insert'
        try:
            self.cursor.execute(query)
            self.db.commit()
        except Exception as e:
            print(f" {text} DB  ", e)

    def update(self, query):
        self.insert(query, 'update')

    def delete(self, query):
        self.insert(query, 'delete')

    def select(self, query):
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
        except Exception as e:
            result = (" select DB err", e)

        return result

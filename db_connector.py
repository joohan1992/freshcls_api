import psycopg2
import psycopg2.extras


class DbConn:
    def __init__(self):
        self.db = psycopg2.connect(host='10.28.100.11', dbname='freshcls', user='postgres', password='ri1234!@', port=5432)
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

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

    def lastpick(self,id=0):
        return self.cursor.fetchone()[id]
    
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
        result = None
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
        except Exception as e:
            results = []

        return result

    def selectAsDict(self, query):
        results = []
        try:
            self.cursor.execute(query)
            columns = list(self.cursor.description)
            result = self.cursor.fetchall()

            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col.name] = row[i]
                results.append(row_dict)
        except Exception as e:
            result = (" select DB err", e)
            print(result)

        return results

from flask import Flask, request, jsonify, render_template, send_from_directory, json
from flask_cors import CORS, cross_origin
import cv2
import flutter_db_connector
import ssl

app = Flask(__name__, template_folder='web')
CORS(app, support_credentials=True)

FLUTTER_WEB_APP = 'web'

@app.route('/test', methods=['POST'])
@cross_origin(origin='*')
def test():
    res=request.get_json()
    print(res)
    return jsonify({'result': 'ok'})

@app.route('/storelist', methods=['POST'])
def storelist():
    res=request.get_json()
    dbConn = flutter_db_connector.DbConn()
    query = f"SELECT STR_NM FROM st_str_mst"
    answer=[i[0] for i in dbConn.select(query=query)]
    del dbConn
    return jsonify({'result': 'ok','answer':answer})


@app.route('/modellist', methods=['POST'])
def modellist():
    query =  "SELECT str_nm,build_req_dt,run_yn,model_stat FROM md_model_mst LEFT JOIN st_str_mst "
    query += "ON md_model_mst.str_no = st_str_mst.str_no "
    answer=dbConn.select(query=query))
    del dbConn
    return jsonify({'result': 'ok','answer':answer)


if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(certfile='server.crt', keyfile='server.key', password='1234')
    app.run(host='0.0.0.0', port=8428, ssl_context=ssl_context, debug=False)
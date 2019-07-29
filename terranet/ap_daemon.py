import json
import sys

from flask import Flask, request, abort, jsonify

app = Flask(__name__)

'''
This minimal flask app provides a way for us to get REST-API calls in the appropriate Namespace.
The Mininet Distribution Node will parse the configuration. 
'''

@app.route('/cfg/', methods=['PUT'])
def set_config():

    data = request.get_json()
    if data is None or 'config' not in data:
        abort(400)

    out = json.dumps(data['config']).strip() + '\n'
    sys.stdout.write(out)  # NOTE: Make sure this is a one-liner
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='::', debug=True, port=6000)



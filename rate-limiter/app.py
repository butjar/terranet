from flask import Flask, request, abort, jsonify

import subprocess


app = Flask(__name__)


def modify_link(dev, rate, burst, latency, delete=False):
    operation = 'del' if delete else 'add'
    args = ['tc', 'qdisc', operation,
            'dev',  '%s' % dev,
            'root',
            'tbf',
            'rate', '%s' % rate,
            'burst', '%s' % burst,
            'latency', '%s' % latency]
    try:
        subprocess.check_output(args=args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        #try to delete previous filter rule
        a = ['tc', 'qdisc', 'del',
            'dev',  '%s' % dev,
            'root']

        try:
            subprocess.check_output(args=a, stderr=subprocess.STDOUT)
            subprocess.check_output(args=args, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e2:
            # old error is more interesting
            raise e


@app.route('/limit/<dev>/', methods=['PUT', 'GET', 'DEL'])
def limit(dev):
    if request.method in ['PUT', 'DEL']:
        data = request.get_json()

        try:
            rate = data['rate']
            burst = data['burst']
            latency = data['latency']
        except KeyError as e:
            print(e)
            abort(400)
            response = {'status': 'failed', 'error': str(e)}
            return jsonify(response)

        try:
            is_delete = True if request.method == 'DEL' else False
            modify_link(dev, rate, burst, latency, delete=is_delete)
            response = {'status': 'ok'}
        except subprocess.CalledProcessError as e:
            response = {'status': 'failed', 'error': repr(e), 'out': str(e.output)}

        return jsonify(response)

    elif request.method == 'GET':
        return jsonify({'dev': dev})
    else:
        abort(404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

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
        subprocess.check_call(args=args)
    except subprocess.CalledProcessError:
        #try to delete previous filter rule
        a = ['tc', 'qdisc', 'del',
            'dev',  '%s' % dev,
            'root']
        subprocess.check_call(args=a)
        subprocess.check_call(args=args)


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
            abort(500)

        try:
            operation = request.method == 'DEL'
            modify_link(dev,rate,burst,latency, delete=operation)
            response = {'status': 'ok'}
        except subprocess.CalledProcessError as e:
            print(e)
            response = {'status': 'failed'}

        return jsonify(response)

    elif request.method == 'GET':
        return dev
    else:
        abort(404)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

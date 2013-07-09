from concurrent import futures
import itertools
import logging

from bottle import abort, get, post, request, run

from .rope.interface import RopeInterface

log = logging.getLogger('traad.server')

# TODO: Is there a way to attach this to every request rather than
# using a global?
project = None

task_ids = itertools.count()
executor = futures.ThreadPoolExecutor(max_workers=1)
tasks = {}

def run_server(port, project_path):
    host = 'localhost'

    log.info(
        'Running traad server for project "{}" at {}:{}'.format(
            project_path,
            host,
            port))

    global project
    project = RopeInterface(project_path)
    run(host=host, port=port)

@get('/task/<task_id>')
def task_status(task_id):
    try:
        task = tasks[int(task_id)]
    except KeyError:
        abort(404, "No task with that ID")

    if task.cancelled():
        return {'status': 'CANCELLED'}
    elif task.running():
        return {'status': 'RUNNING'}
    elif task.done():
        return {'status': 'COMPLETE'}
    else:
        return {'status': 'PENDING'}

@post('/refactor/rename')
def rename_view():
    args = request.json

    log.info('rename: {}'.format(args))

    task_id = next(task_ids)
    tasks[task_id] = executor.submit(
        project.rename,
        new_name=args['name'],
        path=args['path'],
        offset=args.get('offset'))
    return {'task_id': task_id}

@post('/refactor/normalize_arguments')
def normal_arguments_view():
    args = request.json

    log.info('normalize arguments: {}'.format(args))

    task_id = next(task_ids)
    tasks[task_id] = executor.submit(
        project.normalize_arguments,
        path=args['path'],
        offset=args['offset'])
    return {'task_id': task_id}

@post('/refactor/remove_argument')
def remove_argument_view():
    args = request.json

    log.info('remove argument: {}'.format(args))

    task_id = next(task_ids)
    tasks[task_id] = executor.submit(
        project.remove_argument,
        arg_index=args['arg_index'],
        path=args['path'],
        offset=args['offset'])
    return {'task_id': task_id}

@get('/code_assist/completion')
def code_assist_completion_view():
    args = request.json

    log.info('code assist: {}'.format(args))

    return {
        'results': project.code_assist(
            code=args['code'],
            offset=args['offset'],
            path=args['path'])
    }

@get('/code_assist/doc')
def code_assist_doc_view():
    args = request.json

    log.info('get doc: {}'.format(args))

    return {
        'results': project.get_doc(
            code=args['code'],
            offset=args['offset'],
            path=args['path'])
    }

@get('/code_assist/calltip')
def code_assist_calltip_view():
    args = request.json

    log.info('get calltip: {}'.format(args))

    return {
        'results': project.get_calltip(
            code=args['code'],
            offset=args['offset'],
            path=args['path'])
    }

@get('/code_assist/definition')
def code_assist_definition_view():
    args = request.json

    log.info('get definition: {}'.format(args))

    return {
        'results': project.get_definition_location(
            code=args['code'],
            offset=args['offset'],
            path=args['path'])
    }

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Run a traad server.')

    parser.add_argument(
        '-p, --port', metavar='N', type=int,
        dest='port', default=0,
        help='the port on which the server will listen. (0 selects an unused port.)')

    parser.add_argument(
        '-V, --verbosity', metavar='N', type=int,
        dest='verbosity', default=0,
        help='Verbosity level (0=normal, 1=info, 2=debug).')

    parser.add_argument(
        'project', metavar='P', type=str,
        help='the directory containing the project to serve')

    args = parser.parse_args()

    # Configure logging
    level = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }[args.verbosity]

    logging.basicConfig(
        level=level)

    try:
        run_server(args.port, args.project)
    except KeyboardInterrupt:
        # TODO: Executor shutdown?
        log.info('Keyboard interrupt')

if __name__ == '__main__':
    main()

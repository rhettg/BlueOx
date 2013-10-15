"""Hooks for gathering celery task data into blueox.

Importing this module will register signal handlers into Celery worker's runtime.

We also will track creation of tasks on the client side.
"""
import logging
import traceback

import blueox
from blueox.context import current_context
from celery import states
from celery import signals
from django.conf import settings

# If dealer is installed, use it to get our revision
try:
    import dealer.auto
    revision = dealer.auto.auto.revision
except ImportError:
    revision = None

@signals.task_sent.connect
def on_task_sent(**kwargs):
    with blueox.Context('.celery.task_sent'):
        # Arguments for this signal are different than the worker signals. Sometimes
        # they are even different than what the documentation says.
        blueox.set('task_id', kwargs.get('task_id', kwargs['id']))
        blueox.set('task', str(kwargs['task']))
        blueox.set('eta', kwargs['eta'])


@signals.worker_process_init.connect
def on_worker_process_init(**kwargs):
    host = getattr(settings, 'BLUEOX_HOST', '127.0.0.1')
    port = getattr(settings, 'BLUEOX_PORT', 3514)
    blueox.configure(host, port)

    handler = blueox.LogHandler()
    handler.setLevel(logging.INFO)
    logging.getLogger('').addHandler(handler)


@signals.worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    blueox.shutdown()


@signals.task_prerun.connect
def on_task_prerun(**kwargs):
    ctx = blueox.Context(".".join((getattr(settings, 'BLUEOX_NAME', ''), 'celery', 'task')))
    ctx.start()

    ctx.set('task', kwargs['task'].name)
    ctx.set('retries', kwargs['task'].request.retries)
    ctx.set('expires', kwargs['task'].request.expires)
    ctx.set('delivery_info', kwargs['task'].request.delivery_info)
    ctx.set('task_id', str(kwargs['task_id']))
    ctx.set('args', kwargs['args'])
    ctx.set('kwargs', kwargs['kwargs'])

    if revision:
        ctx.set('version', revision)


@signals.task_failure.connect
def on_task_failure(**kwargs):
    blueox.set('exception', "".join(
        traceback.format_exception(*kwargs['einfo'].exc_info)))


@signals.task_retry.connect
def on_task_retry(**kwargs):
    blueox.set('result_state', states.RETRY)

    blueox.set('exception', "".join(
        traceback.format_exception(*kwargs['einfo'].exc_info)))

    # Retry path doesn't call 'postrun'. I think in celery-speak, it's the same
    # task, but we want to track attempts.
    ctx = current_context()
    if ctx:
        ctx.done()


@signals.task_postrun.connect
def on_task_postrun(**kwargs):
    blueox.set('result_state', str(kwargs['state']))

    ctx = current_context()
    if ctx:
        ctx.done()

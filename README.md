BlueOx - A python application logging framework
=========================

BlueOx is a python based logging and data collection framework. The problem it
attempts to solve is one where you have multiple python processes across
multiple hosts processing some sort of requests. You generally want to collect:

  * Performance data (counters, timers, etc)
  * User activity
  * Errors (and debugging data)

Use BlueOx to record that data, aggregate it to a central logging server where
it can be written to disk.

In addition, it's often useful to be able to plug reporting scripts into the
logging server so as to generate live stats and reports or do ad hoc analysis.

BlueOx's collection functionality is fairly advanced allowing heirarchies of
collectors and queuing in the event of failure. For example, it's recommend to
run an instance of `oxd` on each host, and then configure each of those
collectors to forward log events to a central collector on a dedicated log
machine.

BlueOx is named after Paul Bunyan's Blue Ox "Babe". A great help for giant logging problems.

Installation
----------------

BlueOx requires Python 2.7, ZeroMQ and MsgPack.

The full python library requirements are given `requirements.txt` and is designed to be used with virtualenv.

Tornado is not required for operation of BlueOx, but development and running tests will likely require it.

I expect debian packaging will be developed soon.

Application Integration
-----------------

Applications emit BlueOx events by using a context manager and globally accessible BlueOx functions.

Events have a type, which indicates what will be ultimately logged together.

Events also have an id that can be used to tie them together with other related events.

For example, in a web application, an application might choose the use BlueOx as follows:


    def handle(request):
        with blueox.Context('request'):
            blueox.set('user_agent', self.headers['UserAgent'])

            with blueox.timeit('request_time'):
                do_stuff()

            blueox.set('response.status', self.response.status)
            blueox.set('response.size', len(self.response.body))


The above sample would generate one event that contains all the details about a
specific request.

Contexts can be heirarchical. This means you can generate sub-events that
are related to the parent event and can be joined together in post-processing by the common id they share.
Indicate you want this behavior for your context by naming with a prefixing '.'.

For example, inside some application code (in `do_stuff()` above), you might execute some sql queries.

    def execute(cursor, query, args):
        with blueox.Context('.sql'):
            blueox.set('query', query)
            with blueox.timeit('query_time'):
                res = cursor.execute(query, args)
            blueox.set('row_count', len(res))
        return res

Each SQL query would then be logged as a seperate event. However, each event
will have the unique id provided by the parent `request` context. The name of the context will become `request.sql`.

You can provide you're own id or allow BlueOx to autogenerate one for the top-level context.

BlueOx also provides the ability to do sampling. This means only a set
percentage of generate events will actually be logged. You can choose sampling
based on any level of the context:

    with blueox.Context('.memcache', sample=('..', 0.25)):
        blueox.set('key', key)
        client.set(key, value)

In the above example, only 25% of requests will include the memcache data. If
the sample argument where `('memcache', 0.25)` then 25% of all memcache
events would be logged.

### Configuration

If BlueOx has not been explicitly configured, all the calls to BlueOx will essentially be no-ops. This is
rather useful in testing contexts so as to not generate a bunch of bogus data.

For production use, you'll need to set the collection host and port:

    blueox.configure("127.0.0.1", 3514)

### Logging module integration

BlueOx comes with a log handler that can be added to your `logging` module setup for easy integration into existing logging setups.

For example:

    handler = blueox.LogHandler()
    handler.setLevel(logging.INFO)
    logging.getLogger('').addHandler(handler)

By default, all log event will show up as a sub-event `.log` but this can be
configured by passing a type_name to the `LogHandler`

### Tornado Integration

BlueOx comes out of the box with support for Tornado web server. This is
particularly challenging since one of the goals for BlueOx is to, like the
logging module, have globally accessible contexts so you don't have to pass
anything around to have access to all the heirarchical goodness.

Since you'll likely want to have a context per web request, it's difficult o
work around tornado's async machinery to make that work well.
Fear not, batteries included: `blueox.tornado_utils`

The most straightfoward way to integrate BlueOx into a tornado application requires two things:

  1. Allow BlueOx to monkey patch async tooling (tornado.gen primarily)
  1. Use or re-implement the provided base request handler `blueox.tornado_utils.SampleRequestHandler`

To install the monkey patching, add the line:

    blueox.tornado_utils.install()

This must be executed BEFORE any of your RequestHandlers are imported.

This is required if you are using `@web.asynchronous` and `@gen.engine`. If you are
manually managing callbacks (which you probably shouldn't be), you'll need
manually recall the BlueOx context with `self.blueox.start()`

If you are using the `autoreload` module for tornado, you should also add a
call to `shutdown()` as a reload hook to avoid leaking file descriptors.

See `tests/tornado_app.py` for an example of all this.

If you have your own base request handlers you'll likely want to reimplement
based on the one provided rather than trying to use inheritance. This will also
make it really clear what you are including in your top-level event and allow
you to name it whatever you want.


### Django Integration

BlueOx provides middleware that can be plugged in to any Django application.

    MIDDLEWARE_CLASSES.append('blueox.contrib.django.middleware.Middleware')

Default settings should work fine, but BlueOx can be customzized by setting
something like the following:

    BLUEOX_HOST=127.0.0.1
    BLUEOX_PORT=3514
    BLUEOX_NAME='myapp'

The `request` keys are someone similiar between Tornado integration and Django,
except that it's assumed Django is running under WSGI, where certain items like
headers are not given raw.

BlueOx also detects use of 'Dealer' middleware which adds a `revision` key to
your request indicating the SCM version of your application. This will be
included as a `version`.

Event Collection
-----------------

Events are collected by a BlueOx daemon (`oxd`) and can be configured in a variety of topologies.

It's recommended that you run a BlueOx daemon on each host, and then a master BlueOx daemon that collects 
all the streams together for logging. In this configuration, failure of the centralized collector would not
result in any data loss as the local instances would just queue up their events.

So on your local machine, you'd run:

    oxd --forward=master:3514

And on the master collection machine, you'd run:

    oxd --collect="*:3514" --log-path=/var/log/blueox/

Logs are encoded in the MsgPack format (http://msgpack.org/), so you'll need
some tooling for doing log analysis. This is easily done with the tool
`oxview`.

For example:

    cat /var/log/blueox/request.120310.log | oxview

    oxview --log-path=/var/log/blueox --type-name="request" --start-date=20120313 --end-date=20120315

Where `request` is the channel you want to examine.

You can also connect to `oxd` and get a live streaming of log data:

    oxview -H localhost:3513 --type-name="request*"

Note the use of '*' to indicate a prefix query for the type filter. This will
return all events with a type that begins with 'request'

### Dealing with Failure

When an `oxd` instance becomes unavailable, clients will spool messages in
memory up to some internal limit. After hitting this limit, exceptions will be
logged.

For an `oxd` forwarding to another `oxd`, the only limit is how much memory the process can allocate.

### A Note About Ports

There are several types of network ports in use with BlueOx:

  1. Control Port (default 127.0.0.1:3513)
  1. Collection Port (default 127.0.0.1:3514)
  1. Streaming Port (no default, randomonly assigned)

Both the Control and Collection ports are configurable from the command line.

When configuring forwarding between oxd instances, you'll want to always use
the collection port. 

When configuring an application to send data to a oxd instance, you'll want
to use the collection port as well.

For administrative (and `oxview` work) you'll use the control port. The
control port (and BlueOx administrative interface) can be used to discover all
the other ports. The reason the collection port must be configured explicitly
for actual logging purposes is to better handle reconnects and failures.


Administration
---------------
Use the `oxctl` tool to collect useful stats or make other adjustments to a running oxd instance.

For example:

    oxctl



Development
-----------------

Using the magic of Make, virtualenv and pip, setting up your development environment is a snap:

    make dev

This will create a virtualenv in `env` directory. Running the tests is just a simple:

    make test

Or if you are running individual tests, use `testify` directly:

    testify -v tests


TODO List
----------------
  * Failure of the central collector is only recoverable if the `oxd`
    instance comes back on the same ip address. It would be nice
    to be able to live reconfigure through `oxctl` to point to a backup collector.
  * Debian packaging would probably be convinient.
  * Need more Real World data on what becomes a bottleneck first: CPU or
    Network. Adding options for compression would be pretty easy.
  * More examples of what to do with the data would make this project more compelling visually.


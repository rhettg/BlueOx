Ziggy - A python application logging framework
=========================

Installation
----------------

Ziggy requires ZeroMQ and Python 2.7

The python library requirements are given `requirements.txt` and is designed to be used with virtualenv.

I expect debian packaging will be developed soon.

Application Integration
-----------------

Applications emit ziggy events by using a context manager and globally accessible ziggy functions.

Events have a type, which indicates what will be ultimately logged together.

Events also have an id that can be used to tie them together with other related events.

For example, in a web application, an application might choose the use ziggy as follows:


    def handle(request):
        with ziggy.Context('request'):
            ziggy.set('user_agent', self.headers['UserAgent'])

            with ziggy.timeit('request_time'):
                do_stuff()

            ziggy.set('response.status', self.response.status)
            ziggy.set('response.size', len(self.response.body))


The above sample would generate one event that contains all the details about a
specific request.

Contexts can be heirarchical. This means you can generate sub-events that
are related to the parent event and can be joined together in post-processing by the common id they share.
Indicate you want this behavior for your context by naming with a prefixing '.'.

For example, inside some application code (in `do_stuff()` above), you might execute some sql queries.

    def execute(cursor, query, args):
        with ziggy.Context('.sql'):
            ziggy.set('query', query)
            with ziggy.timeit('query_time'):
                res = cursor.execute(query, args)
            ziggy.set('row_count', len(res))
        return res

Each SQL query would then be logged as a seperate event. However, each event
will have the unique id provided by the parent `request` context. The name of the context will become `request.sql`.

You can provide you're own id or allow ziggy to autogenerate one for the top-level context.

Ziggy also provides the ability to do sampling. This means only a set
percentage of generate events will actually be logged. You can choose sampling
based on any level of the context:

    with ziggy.Context('.memcache', sample=('..', 0.25)):
        ziggy.set('key', key)
        client.set(key, value)

In the above example, only 25% of requests will include the memcache data. If
the sample argument where `('memcache', 0.25)` then 25% of all memcache
events would be logged.

### Configuration

If ziggy has not been explicitly configured, all the calls to ziggy will essentially be no-ops. This is
rather useful in testing contexts so as to not generate a bunch of bogus data.

For production use, you'll need to set the collection host and port:

    ziggy.configure("127.0.0.1", 3514)

### Tornado Hooks

Ziggy comes out of the box with support for Tornado web server. This is
particularly challenging since one of the goals for ziggy is to, like the
logging module, have globally accessible contexts so you don't have to pass
anything around to have access to all the heirarchical goodness.

Since you'll likely want to have a context per web request, it's difficult o
work around tornado's async machinery to make that work well.
Fear not, batteries included: `ziggy.tornado_utils`

The most straightfoward way to integrate ziggy into a tornado application requires two things:

  1. Allow ziggy to monkey patch async tooling (tornado.gen primarily)
  1. Use or re-implement the provided base request handler `ziggy.tornado_utils.SampleRequestHandler`

To install the monkey patching, add the line:

    ziggy.tornado_utils.install()

This must be executed BEFORE any of your RequestHandlers are imported.

This is required if you are using `@web.asynchronous` and `@gen.engine`. If you are
manually managing callbacks (which you probably shouldn't be), you'll need
manually recall the ziggy context with `self.ziggy.start()`

See `tests/tornado_app.py` for an example of all this.

If you have your own base request handlers you'll likely want to reimplement
based on the one provided rather than trying to use inheritance. This will also
make it really clear what you are including in your top-level event and allow
you to name it whatever you want.


Event Collection
-----------------

Events are collected by a ziggy daemon (`ziggyd`) and can be configured in a variety of topologies.

It's recommended that you run a ziggy daemon on each host, and then a master ziggy daemon that collects 
all the streams together for logging. In this configuration, failure of the centralized collector would not
result in any data loss as the local instances would just queue up their events.

So on your local machine, you'd run:

    ziggyd --forward=master:3514

And on the master collection machine, you'd run:

    ziggyd --collect="*:3514" --log-path=/var/log/ziggy/

Logs are stored in BSON format, so you'll need some tooling for doing log
analysis. This is easily done with the tool `ziggyview`.

For example:

    cat /var/log/ziggy/request.120310.bson | ziggyview

    ziggyview --log-path=/var/log/ziggy --type-name="request" --start-date=20120313 --end-date=20120315

Where `request` is the channel you want to examine.

You can also connect to `ziggyd` and get a live streaming of log data:

    ziggyview -H localhost:3513 --type-name="request*"

Note the use of '*' to indicate a prefix query for the type filter. This will
return all events with a type that begins with 'request'

### A Note About Ports

There are several types of network ports in use with Ziggy:

  1. Control Port (default 127.0.0.1:3513)
  1. Collection Port (default 127.0.0.1:3514)
  1. Streaming Port (no default, randomonly assigned)

Both the Control and Collection ports are configurable from the command line.

When configuring forwarding between ziggyd instances, you'll want to always use
the collection port. 

When configuring an application to send data to a ziggyd instance, you'll want
to use the collection port as well.

For administrative (and `ziggyview` work) you'll use the control port. The
control port (and ziggy administrative interface) can be used to discover all
the other ports. The reason the collection port must be configured explicitly
for actual logging purposes is to better handle reconnects and failures.


Administration
---------------
Use the `ziggyctl` tool to collect useful stats or make other adjustments to a running ziggyd instance.

For example:

    ziggyctl status

or

    ziggyctl shutdown


Development
-----------------

Using the magic of Make, virtualenv and pip, setting up your development environment is a snap:

    make dev

This will create a virtualenv in `env` directory. Running the tests is just a simple:

    make test

Or if you are running individual tests, use `testify` directly:

    testify -v tests


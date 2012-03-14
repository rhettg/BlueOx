Ziggy - A python application logging framework
=========================

Installation
----------------

Ziggy requires ZeroMQ and Python 2.7

The python library requirements are given `requirements.txt` and is designed to be used with virtualenv.

I expect debian packaging will be developed soon.

Development
-----------------

Using the magic of Make, virtualenv and pip, setting up your development environment is a snap:

    make dev

This will create a virtualenv in `env` directory. Running the tests is just a simple:

    make test

Or if you are running individual tests, use `testify` directly:

    testify -v tests

Application Integration
-----------------

Applications emit ziggy events by using a context manager and globally accessible ziggy functions.

Events have a type, which indicates what will be ultimately logged together.

Events also have an id that can be used to tie them together.

For example, in a web application, an application might choose the use ziggy as follows:

    def handle(request):
        with ziggy.Context('request', unique_id):
            ziggy.set('user_agent', self.headers['UserAgent'])

            with ziggy.timeit('request_time'):
                do_stuff()

            ziggy.set('response.status', self.response.status)
            ziggy.set('response.size', len(self.response.body))


The above sample would generate one event that contains all the details about a
specific request.

Contexts can also be heirarchical. This means you can generate sub-events that
are related to the parent event and can be joined together in post-processing.

For example, inside some application code (in `do_stuff()` above), you might execute some sql queries.

    def execute(cursor, query, args):
        with ziggy.Context('request.sql'):
            ziggy.set('query', query)
            with ziggy.timeit('query_time'):
                res = cursor.execute(query, args)
            ziggy.set('row_count', len(res))
        return res

Each SQL query would then be logged as a seperate event. However, each event
will have the unique id provided by the parent `request` context.

Ziggy also provides the ability to do sampling. This means only a set
percentage of generate events will actually be logged. You can choose sampling
based on any level of the context:

    with ziggy.Context('request.memcache', sample=('request', 0.25)):
        ziggy.set('key', key)
        client.set(key, value)

In the above example, only 25% of requests will include the memcache data. If
the sample argument where `('request.memcache', 0.25)` then 25% of all memcache
events would be logged.

Event Collection
-----------------

Events are collected by a ziggy daemon (`ziggyd`) and can be configured in a variety of topologies.

It's recommended that you run a ziggy daemon on each host, and then a master ziggy daemon that collects 
all the streams together for logging. In this configuration, failure of the centralized collector would not
result in any data loss as the local instances would just queue up their events.

So on your local machine, you'd run:

    ziggyd -H localhost:3514 --publish=master:3514

And on the master collection machine, you'd run:

    ziggyd -H localhost:3514 --log-path=/var/log/ziggy/

Logs are stored in BSON format, so you'll need some tooling for doing log analysis. This is easily done with the tool `ziggyview`.

For example:

    cat /var/log/ziggy/request.120310.bson | ziggyview

    ziggyview --log-path=/var/log/ziggy request --start-date=20120313 --end-date=20120315

Where `request` is the channel you want to examine.

You can also connect to `ziggyd` and get a live streaming of log data:

    ziggyview -H localhost:3514 request


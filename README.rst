Ziggy - A python application logging framework
=========================

Application Usage
-----------------

Applications emit ziggy events that belong in channels and are part of a larger context.

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

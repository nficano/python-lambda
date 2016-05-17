# -*- coding: utf-8 -*-


def handler(event, context):
    # Your code goes here!
    context_val = context.client_context.custom.foo
    assert context_val == 'bar'
    e = event.get('e')
    pi = event.get('pi')
    return e + pi

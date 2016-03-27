# -*- coding: utf-8 -*-


def handler(event, context):
    # You code goes here!
    e = event.get('e')
    pi = event.get('pi')
    print "your test handler was successfully invoked!"
    return e + pi

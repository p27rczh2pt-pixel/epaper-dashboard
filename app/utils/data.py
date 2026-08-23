def dig(d, *keys, default=None):
    """Safely walk a chain of nested dict keys, returning `default` on any miss."""
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur

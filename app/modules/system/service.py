import time

start_time = time.time()


def get_app_uptime():
    """Returns the app uptime in seconds."""
    return int(time.time() - start_time)


def get_app_uptime_formatted():
    """Returns the app uptime in a human-readable format."""
    uptime_secs = get_app_uptime()
    hours, remainder = divmod(uptime_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)

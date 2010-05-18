from httpproxy import settings

def get_proxy_infos(*args, **kwargs):
    domain = 'proxy_domain' in kwargs and kwargs['proxy_domain'] or settings.PROXY_DOMAIN
    port = 'proxy_port' in kwargs and kwargs['proxy_port'] or settings.PROXY_PORT
    user = 'proxy_user' in kwargs and kwargs['proxy_user'] or hasattr(settings, 'PROXY_USER') and settings.PROXY_USER or None
    password = 'proxy_password' in kwargs and kwargs['proxy_password'] or hasattr(settings, 'PROXY_PASSWORD') and settings.PROXY_PASSWORD or None
    return (domain, port, user, password)


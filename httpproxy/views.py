import httplib2
 
from django.http import HttpResponse
from django.utils.encoding import smart_unicode

from httpproxy import settings
from httpproxy.exceptions import UnkownProxyMode
from httpproxy.decorators import normalize_request, rewrite_response
from httpproxy.utils import get_proxy_infos

def proxy(request, *args, **kwargs):
    conn = httplib2.Http()
    url = request.path
    
    (domain, port, user, password, cookie) = get_proxy_infos(*args, **kwargs)
    
    # Optionally provide authentication for server
    if user and password:
        conn.add_credentials(user, password)
    
    PROXY_FORMAT = u'http://%s:%d%s' % (domain, port, u'%s')
    
    headers = {}
    if cookie:
        headers = {"Cookie": cookie}
    
    if request.method == 'GET' or request.method == "HEAD":
        url_ending = '%s?%s' % (url, request.GET.urlencode())
        url = PROXY_FORMAT % url_ending
        response, content = conn.request(url, request.method, headers=headers)
    else:
        url = PROXY_FORMAT % url
        data = request.POST.urlencode()
        response, content = conn.request(url, request.method, data, headers=headers)
    if settings.PROXY_CONVERT_CHARSET:
        # This is a pretty naive implementation, since the content-type header
        # might be not used by the remote resource...
        splitted_type = response['content-type'].split('charset=')
        [encoding] = splitted_type[-1:]
        mimetype = splitted_type[0].split(';')[0]
        if len(splitted_type) > 1 and encoding.upper() != 'UTF-8':
            content = smart_unicode(content, encoding)
            response['content-type'] = response['content-type'].replace(encoding, 'UTF-8')
            if mimetype in ('text/html', 'application/xml', 'text/xml'):
                # <?xml ... encoding="***"?>
                content = content.replace('encoding="%s"' % (encoding, ), 'encoding="UTF-8"')
            if mimetype == 'text/html':
                # <meta ... charset=***">
                content = content.replace('charset=%s' % (encoding, ), 'charset=UTF-8')
    return HttpResponse(content, status=int(response['status']), mimetype=response['content-type'])


if settings.PROXY_MODE is not None:
    proxy_mode = settings.PROXY_MODE
    try:
        decorator = getattr(__import__('httpproxy' + '.decorators', fromlist=proxy_mode), proxy_mode)
    except AttributeError, e:
        raise UnkownProxyMode('The proxy mode "%s" could not be found. Please specify a corresponding decorator function in "%s.decorators".' % (proxy_mode, 'httpproxy'))
    else:
        proxy = decorator(proxy)

if settings.PROXY_REWRITE_RESPONSES:
    proxy = rewrite_response(proxy)

# The request object should always be normalized
proxy = normalize_request(proxy)

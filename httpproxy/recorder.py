import logging

from django.http import HttpResponse

from httpproxy.exceptions import RequestNotRecorded
from httpproxy.models import Request, Response


logger = logging.getLogger('httpproxy')
logger.setLevel(logging.DEBUG)

class ProxyRecorder(object):
    """
    Facilitates recording and playback of Django HTTP requests and responses.
    """
    
    def __init__(self, domain, port=80):
        super(ProxyRecorder, self).__init__()
        self.domain, self.port = domain, port
    
    def record_request(self, request):
        """
        Saves the provided request, including its parameters.
        """
        logger.info('Recording: GET "%s"' % self._request_string(request))
        
        recorded_request, created = Request.objects.get_or_create(
            domain=self.domain,
            port=self.port,
            path=request.path,
            querystring=request.GET.urlencode(),
        )
        
        # Update the timestamp on the existing recorded request
        if not created:
            recorded_request.save()
        
        return recorded_request
    
    def record_response(self, recorded_request, response):
        """
        Records a response so it can be replayed at a later stage.
        
        The recorded response is linked to a previously recorded request and
        its request parameters to allow for reverse-finding the recorded
        response given the recorded request object.
        """
        
        # Delete the previously recorded response, if any
        try:
            recorded_request.response.delete()
        except Response.DoesNotExist:
            pass
        
        # Extract the encoding from the response
        content_type = response['Content-Type']
        encoding = content_type.partition('charset=')[-1] or 'utf-8'

        # Record the new response
        Response.objects.create(
            request=recorded_request,
            status=response.status_code,
            content_type=content_type,
            content=response.content.decode(encoding), 
        )
    
    def playback_response(self, request):
        """
        Returns a previously recorded response based on the provided request.
        """
        try:
            matching_request = Request.objects.filter(
                domain=self.domain, 
                path=request.path, 
                querystring=request.GET.urlencode()
            ).latest()
        except Request.DoesNotExist, e:
            raise RequestNotRecorded('The request made has not been recorded yet. Please run httpproxy in "record" mode first.')
        
        logger.info('Playback: GET "%s"' % self._request_string(request))
        response = matching_request.response # TODO handle "no response" situation
        encoding = self._get_encoding(response.content_type)
        
        return HttpResponse(
            response.content.encode(encoding), 
            status=response.status, 
            mimetype=response.content_type
        )
    
    def _get_encoding(self, content_type):
        """
        Extracts the character encoding from a HTTP Content-Type header.
        """
        return content_type.partition('charset=')[-1] or 'utf-8'
        
    def _request_string(self, request):
        """
        Helper for getting a string representation of a request.
        """
        return '%(domain)s:%(port)d%(path)s"' % {
            'domain': self.domain, 
            'port': self.port, 
            'path': request.get_full_path()
        }
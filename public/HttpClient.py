# -*- coding: utf-8 -*-
"""__author__ = 'jiazhu'"""
import logging
import re
import time

import requests
from requests import Response, Request
from requests.exceptions import (RequestException, MissingSchema,
    InvalidSchema, InvalidURL)
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from public import Events

absolute_http_url_regexp = re.compile(r"^https?://", re.I)


class LocustResponse(Response):

    def raise_for_status(self):
        if hasattr(self, 'error') and self.error:
            raise self.error
        Response.raise_for_status(self)


class HttpClient(requests.Session):
    """
    Class for performing web requests and holding (session-) cookies between requests (in order
    to be able to log in and out of websites). Each request is logged so that locust can display 
    statistics.
    
    This is a slightly extended version of `python-request <http://python-requests.org>`_'s
    :py:class:`requests.Session` class and mostly this class works exactly the same. However 
    the methods for making requests (get, post, delete, put, head, options, patch, request) 
    can now take a *url* argument that's only the path part of the URL, in which case the host 
    part of the URL will be prepended with the HttpSession.base_url which is normally inherited
    from a Locust class' host property.
    
    Each of the methods for making requests also takes two additional optional arguments which 
    are Locust specific and doesn't exist in python-requests. These are:
    
    :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path. 
                 This can be used to group different URL's that are requested into a single entry in Locust's statistics.
    :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager 
                           to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the 
                           response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
                           and then mark it as successful even if the response code was not (i.e 500 or 404).
    """
    def __init__(self, base_url, log_name="MXTest", *args, **kwargs):
        requests.Session.__init__(self)
        self.base_url = base_url
        self._logger = logging.getLogger(log_name)
        self._logger_db = logging.getLogger("Result")
        self._logger_cn = logging.getLogger("Count")

    def _build_url(self, path):
        """ prepend url with hostname unless it's already an absolute URL """
        if absolute_http_url_regexp.match(path):
            return path
        else:
            return "%s%s" % (self.base_url, path)

    def request(self, method, url, name=None, catch_response=False, **kwargs):
        """
        Constructs and sends a :py:class:`requests.Request`.
        Returns :py:class:`requests.Response` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path. 
          This can be used to group different URL's that are requested into a single entry in Locust's statistics.
        :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager 
          to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the 
          response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
          and then mark it as successful even if the response code was not (i.e 500 or 404).
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary or bytes to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects`` for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send data before giving up, as a float, 
            or a (`connect timeout, read timeout <user/advanced.html#timeouts>`_) tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param stream: (optional) whether to immediately download the response content. Defaults to ``False``.
        :param verify: (optional) if ``True``, the SSL cert will be verified. A CA_BUNDLE path can also be provided.
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
        """
        
        # prepend url with hostname unless it's already an absolute URL
        url = self._build_url(url)

        # store meta data that is used when reporting the request to locust's statistics
        request_meta = {}
        
        # set up pre_request hook for attaching meta data to the request object
        request_meta["url"] = url
        request_meta["method"] = method
        request_meta["start_time"] = time.time()
        
        response = self._send_request_safe_mode(method, url, **kwargs)
        
        # record the consumed time
        request_meta["response_time"] = int((time.time() - request_meta["start_time"]) * 1000)

        request_meta["name"] = name or (response.history and response.history[0] or response).request.path_url
        
        # get the length of the content, but if the argument stream is set to True, we take
        # the size from the content-length header, in order to not trigger fetching of the body
        if kwargs.get("stream", False):
            request_meta["content_size"] = int(response.headers.get("content-length") or 0)
        else:
            request_meta["content_size"] = len(response.content or "")

        try:
            response.raise_for_status()
        except RequestException as e:

            self._logger.info("events.request_failure.fire" + str(request_meta["response_time"]) + "== " + str(
                response.headers) + " ==" + str(response.status_code))
            self._logger_cn.info("name:"+request_meta["name"]+" request_failure:" +
                                 str(response.status_code) + " ==" + str(request_meta["response_time"]))

            # Log detail response when fail, and don't do that when success.
            self._logger_db.info("failure:"+str(request_meta) +
                                 "  response.status_code:" + str(response.status_code) +
                                 "  exception:" + str(e) +
                                 "  response.headers:"+str(response.headers) +
                                 "  response.text:"+str(response.text) +
                                 "  request_kwargs:" + str(kwargs)
                                 )
            Events.request_failure.fire(
                request_type=request_meta["method"],
                name=request_meta["name"],
                response_time=request_meta["response_time"],
                response_headers=response.headers,
                response_text=response.text,
                response_status_code=response.status_code,
                exception=e,
            )
        else:
            self._logger.info("events.request_success.fire")
            self._logger_cn.info("name:"+request_meta["name"]+" request_success:" + str(response.status_code) + " ==" + str(
                request_meta["response_time"]))

            self._logger_db.info("success:" + str(request_meta)+
                                 "  response.status_code:" + str(response.status_code)+\
                                 "  response.headers:"+str(response.headers)+\
                                 "  response.text:"+str(response.text))
            Events.request_success.fire(
                request_type=request_meta["method"],
                name=request_meta["name"],
                response_time=request_meta["response_time"],
                response_length=request_meta["content_size"],
                response_headers=response.headers,
                response_status_code=response.status_code
            )
        return response

    def _send_request_safe_mode(self, method, url, **kwargs):
        """
        Send an HTTP request, and catch any exception that might occur due to connection problems.

        Safe mode has been removed from requests 1.x.
        """
        try:
            return requests.Session.request(self, method, url, **kwargs)
        except (MissingSchema, InvalidSchema, InvalidURL):
            raise
        except RequestException as e:
            r = LocustResponse()
            r.error = e
            r.status_code = 0  # with this status_code, content returns None
            r.request = Request(method, url).prepare()
            return r

    def _send_request_unsafe_mode(self, method, url, **kwargs):
        """
        Send an HTTP request, and catch any exception that might occur due to connection problems.

        Safe mode has been removed from requests 1.x.
        """
        try:
            return requests.request(method, url, **kwargs)
        except (MissingSchema, InvalidSchema, InvalidURL):
            raise
        except RequestException as e:
            r = LocustResponse()
            r.error = e
            r.status_code = 0  # with this status_code, content returns None
            r.request = Request(method, url).prepare()
            return r
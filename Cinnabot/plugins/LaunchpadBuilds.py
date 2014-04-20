#! /usr/bin/python
# -*- coding=utf-8 -*-

from Cinnabot.BasePlugin import BasePlugin
import urllib
import urlparse
import libxml2
import logging
import json
import httplib2

class HTMLNode(object):
    def __init__(self, xml_node):
        self._xml_node = xml_node
    
    def find(self, elname = None, maxdepth = -1, **params):
        res = []
        if elname == None or self._xml_node.name == elname:
            add = True
            for i in params:
                if self._xml_node.prop(i) != params[i]:
                    add = False
                    break
            if add:
                res.append(self)
        if maxdepth!=0:
            child = self._xml_node.children
            while child:
                res += HTMLNode(child).find(elname, maxdepth - 1, **params)
                child = child.next
        return res
    
    def _get_next(self):
        if self._xml_node.next:
            return HTMLNode(self._xml_node.next)
        else:
            return None
    next = property(_get_next)
    
    def getContent(self):
        return self._xml_node.getContent()
    
    def prop(self, *args):
        return self._xml_node.prop(*args)
    
    def _get_children(self):
        children = self._xml_node.children
        if children:
            return HTMLNode(children)
        else:
            return children
    children = property(_get_children)
    
    def _get_parent(self):
        parent = self._xml_node.parent
        if parent:
            return HTMLNode(parent)
        else:
            return parent
    parent = property(_get_parent)

class LaunchpadBuildsPlugin(BasePlugin):
    def __init__(self, bot, plugin_name):
        BasePlugin.__init__(self, bot, plugin_name)
        
        bot._irc.execute_every(900, self._check_failed_builds)
        self._check_failed_builds()
        
        self._known_builds = []
        self._has_run = False
        self._last_date = None
    
    def unload(self):
        self._unloaded = True
    
    def _check_failed_builds(self):
        if hasattr(self, "_unloaded") and self._unloaded:
            return
        
        self._start_task(self._do_check_failed_builds)
    
    def _shorten_url(self, url):
        try:
            c = httplib2.Http()
            resp, content = c.request("https://www.googleapis.com/urlshortener/v1/url?key=" + self._get_config("google_url_shortener_api_key"), "POST", headers = {"Content-Type": "application/json"}, body = json.dumps({"longUrl": url}))
            res = json.loads(content)["id"]
        except:
            res = url
        return res
    
    def _do_check_failed_builds(self):
        logging.info("LaunchpadBuildsPlugin:_do_check_failed_builds")
        
        url = "https://launchpad.net/~gwendal-lebihan-dev/+archive/cinnamon-nightly/+builds?build_text=&build_state=failed&batch=200"
        filename, msg = urllib.urlretrieve(url)
        tree = HTMLNode(libxml2.htmlParseFile(filename, "utf-8").getRootElement())
        
        for build_tr in tree.find("table", **{'class': 'listing'})[0].find("tr"):
            title = None
            log_link = None
            build_link = None
            build_id = None
            is_failed = False
            build_date = None
            for a in build_tr.find("a"):
                if a.getContent().rstrip().lstrip() == "see the log":
                    log_link = urlparse.urljoin(url, a.prop("href"))
                elif "/+build/" in a.prop("href"):
                    build_id = a.prop("href").split("/")[-1]
                    build_link = urlparse.urljoin(url, a.prop("href"))
                    title = a.getContent().rstrip().lstrip()
            img = build_tr.find("img")
            if len(img) == 1 and img[0].prop("src") != None and img[0].prop("src").endswith("/build-failed"):
                is_failed = True
            spans = build_tr.find("span")
            if len(spans) > 0:
                build_date = spans[0].getContent()[3:]
            if build_link != None and title != None and log_link != None and build_id != None and is_failed and build_date != None and (self._last_date == None or build_date >= self._last_date):
                if self._last_date == None:
                    self._last_date = build_date
                else:
                    self._last_date = max(self._last_date, build_date)
                if not self._has_run:
                    self._known_builds.append(build_id)
                else:
                    if not build_id in self._known_builds:
                        self._known_builds.append(build_id)
                        package = title.split(" ")[3]
                        return self.privmsg_response(self._get_config("output_channel"), u"[\x0313%s\x0f] \x0305\x02Failed build: \x0f%s \x0302\x1f%s\x0f, build log : \x0302\x1f%s\x0f" % (package, title, self._shorten_url(build_link), self._shorten_url(log_link)))
        
        self._has_run = True

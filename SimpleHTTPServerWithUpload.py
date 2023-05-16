#!/usr/bin/env python
# -*- coding: utf-8 -*-
# modifyDate: 20120808 ~ 20200609
# 原作者为：bones7456, http://li2z.cn/
# 修改者为: xcxinghai@xinghaixu.com
# 再修改者: Mr-Lander,https://github.com/Mr-lander
# v1.2，changeLog：
# +: 文件日期/时间/颜色显示、多线程支持、主页跳转
# -: 解决不同浏览器下上传文件名乱码问题：仅IE，其它浏览器暂时没处理。
# -: 一些路径显示的bug，主要是 cgi.escape() 转义问题
# ?: notepad++ 下直接编译的server路径问题
# v1.3 changeLog
# 支持 curl -X POST -F file=@ScreenFloat.zip http://XXXXX.com:8001 的方式上传文件
# 修复各个浏览器上传文件名乱码问题。
# sys.stdout.flush() 强制刷新缓冲区，避免print的数据日志不生效
# v1.4 changeLog:
# 修改过时的import 方法 ：from io import BytesIO;from
# content = f.getvalue().encode('utf-8')  # 将 StringIO 的内容转化为字节流
# 本人做的工作只是将2.7不可用的代码段更换为python3.x支持的版本，非常感谢前人搭的梯子

"""
    简介：这是一个 python 写的轻量级的文件共享服务器（基于内置的SimpleHTTPServer模块），
    支持文件上传下载，只要你安装了python（建议版本3.x,不再支持2.x），
    然后去到想要共享的目录下，执行：
        python SimpleHTTPServerWithUpload.py 1234
    其中1234为你指定的端口号，如不写，默认为 8080
    然后访问 http://localhost:1234 即可，localhost 或者 1234 请酌情替换。
"""

"""Simple HTTP Server With Upload.

This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

"""

__version__ = "1.4"
__all__ = ["SimpleHTTPRequestHandler"]
__author__ = "Mr-lander"
__home_page__ = "https://github.com/Mr-lander/SimpleHTTPServer_local_python3.x"

import io
import os
import sys
import posixpath
import http.server as BaseHTTPServer
from socketserver import ThreadingMixIn
import threading
import urllib
from html import escape
import cgi
import shutil
import mimetypes
import re
import html
import html.parser as HTMLParser

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

def showTips():
    print( "" )
    print ('----------------------------------------------------------------------->> ')
    try:
        port = int(sys.argv[1])
    except Exception as e:
        print ('-------->> Warning: Port is not given, will use deafult port: 8001 ')
        print ('-------->> if you want to use other port, please execute: ')
        print ('-------->> python SimpleHTTPServerWithUpload.py port ')
        print ("-------->> port is a integer and it's range: 1024 < port < 65535 ")
        port = 8001

    #if not 1024 < port < 65535:  port = 8080
    # serveraddr = ('', port)
    print ('-------->> Now, listening at port ' + str(port) + ' ...')
    print( '----------------------------------------------------------------------->> ')
    print ("")
    sys.stdout.flush()
    return ('', port)


class SimpleHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    server_version = "SimpleHTTPWithUpload/" + __version__

    def do_GET(self):
        """Serve a GET request."""

        f = self.send_head()
        if f:
            content = f.getvalue().encode('utf-8')  # 将 StringIO 的内容转化为字节
            self.wfile.write(content)  # 将字节写入到 wfile
            f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)
        sys.stdout.flush()
        f = StringIO()
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<head>\n<meta content=\"text/html; charset=UTF-8\" http-equiv=\"Content-Type\">\n")
        f.write("<title>Upload Result Page</title>\n")
        f.write("<body>\n<h2>Upload Result Page</h2>\n")
        f.write("<hr>\n")
        if r:
            f.write("<strong>Success:</strong>")
        else:
            f.write("<strong>Failed:</strong>")
        f.write(info)
        if 'referer' in self.headers:
            f.write("<br><a href=\"%s\">back</a>" % self.headers['referer'])
        f.write("<hr><small>Powerd By: bones7456, check new version at ")
        f.write("<a href=\"http://li2z.cn/?s=SimpleHTTPServerWithUpload\">")
        f.write("here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            content = f.getvalue().encode('utf-8')  # 将 StringIO 的内容转化为字节
            self.wfile.write(content)  # 将字节写入到 wfile
            f.close()

    def deal_post_data(self):
        #获取boundary —— 更改
        content_type = self.headers['Content-Type']
        ctype, pdict = cgi.parse_header(content_type)
        if ctype == 'multipart/form-data':
            boundary = pdict['boundary'].encode()  # 将 boundary 转换为字节串
        remainbytes = int(self.headers['content-length'])

        line = self.rfile.readline()
        remainbytes -= len(line)


        if not boundary in line:
            return (False, "Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode('utf-8'))
        if not fn:
            return (False, "Can't find out file name...")
        path = self.translate_path(self.path)
        # 对中文进行处理
        myHtmlParser = html.parser.HTMLParser()
        parserFn = html.unescape(fn[0])
        fn = os.path.join(path, parserFn)
        print (fn)
        sys.stdout.flush()

        # 对重复文件的处理方式，根据自己的需求，自己定制
        #  while os.path.exists(fn):
            #  fn += "_"
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False, "Can't create file to write, do you have permission to write?")

        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, "File '%s' upload success!" % fn)
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpect Ends of data.")

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<head>\n<meta content=\"text/html; charset=UTF-8\" http-equiv=\"Content-Type\">\n")
        f.write("<title>Directory listing for %s</title>\n</head>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n")
        f.write("<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write("<input name=\"file\" type=\"file\"/>")
        f.write("<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.parse.unquote(linkname), html.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })

class ThreadingServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

def test(HandlerClass = SimpleHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    BaseHTTPServer.test(HandlerClass, ServerClass)

if __name__ == '__main__':
    serveraddr = showTips()

    #  test()

    #单线程
    # srvr = BaseHTTPServer.HTTPServer(serveraddr, SimpleHTTPRequestHandler)

    #多线程
    srvr = ThreadingServer(serveraddr, SimpleHTTPRequestHandler)
    srvr.serve_forever()

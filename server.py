#!/usr/bin/python3

from collections import OrderedDict

from fix.network  import  Server

def main():
    srv = Server ('127.0.0.1',  9120)
    srv.start()
    
if __name__ == '__main__':
    main()

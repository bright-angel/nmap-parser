# -*- encoding: utf-8 -*-

'''
@File    :   __main__.py
@Time    :   2026/06/15
@Author  :   test233
@Version :   1.0.0
'''

"""
Entry point for python -m nmap_parser
Launches GUI by default, or CLI if arguments are provided.
"""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from nmap_parser.cli import main
    else:
        from nmap_parser.gui import main
    main()

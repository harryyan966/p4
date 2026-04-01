"""Example Usages of utils.py"""

from utils import *

def main():
    # logs = get_trader_logs("26721")
    # logs = get_trader_logs("33234")
    logs = get_trader_logs("33608")
    # for _, log in logs.items():
    #     clear_console()
    #     print_log_item(log, wall_mid_formula)
    #     input()

    print_log_item(logs[12800], products=["TOMATOES"])
    print_log_item(logs[12900], products=["TOMATOES"])
    
    # get_snapshots(logs, "TOMATOES")

main()
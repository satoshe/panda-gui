"""
Example program to demonstrate Gooey's presentation of subparsers
"""
import sys
import argparse
import time
import requests
from gooey import Gooey, GooeyParser
import json
import subprocess
from nacl.encoding import HexEncoder, RawEncoder
from nacl.signing import SigningKey, VerifyKey
import hashlib
import os
from os.path import exists
import nacl.hash
import time
import random, string

DEFAULT_TIMEOUT = 4

class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

import sys
sys.stdout = Unbuffered(sys.stdout)

import sys, os
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

def printToConsole(s):
    print(s)

def display_message():
    if sys.argv[1] == 'Check-Balance':
        to_check = sys.argv[3]
        printToConsole("Loading balance for " + to_check)
        servers = json.loads(requests.get('http://ec2-34-218-176-84.us-west-2.compute.amazonaws.com/hosts',timeout=DEFAULT_TIMEOUT).text)
        for server in servers:
            try:
                balance = json.loads(requests.get(server + "/ledger/" + to_check, timeout=DEFAULT_TIMEOUT).text)
                if 'error' in balance.keys():
                    print ("Wallet not found on " + server)
                else:
                    print ("Balance from " + server + " is:")
                    print (str(balance["balance"]/10000))
            except:
                continue
    elif sys.argv[1] == 'Create-Wallet':
        path = sys.argv[3]
        if (exists(path)):
            printToConsole("[ERROR] File : " + path + " already exists.")
        else:
            printToConsole("======GENERATING WALLET=======")
            time.sleep(1)
            output = subprocess.check_output([application_path + '/keygen', path])
            wallet = json.loads(open(path, "r").read())["wallet"]
            printToConsole("[SUCCESS] Key file : " + path + " saved")
            printToConsole("New wallet address is: " + wallet)
    elif sys.argv[1] == 'Send-Coins':
        retries = int(sys.argv[3])
        blockDelta = int(sys.argv[5])
        keyFile = sys.argv[7]
        toWallet = sys.argv[8]
        amount = float(sys.argv[9])
        fee = float(sys.argv[10])
        printToConsole("[STATUS] Starting send")
        for i in range(0, retries):
            printToConsole("[STATUS] Sending transaction (Attempt " + str(i+1) + ")")
            servers =  json.loads(requests.get('http://ec2-34-218-176-84.us-west-2.compute.amazonaws.com/hosts',timeout=DEFAULT_TIMEOUT).text)
            bestCount = 0
            bestServers = []
            # fetch the best server
            for server in servers:
                # get block count:
                try:
                    num = int(requests.get(server + "/block_count", timeout=DEFAULT_TIMEOUT).text)
                    if num > bestCount:
                        bestServers = [server]
                        bestCount = num
                    elif num == bestCount:
                        bestServers.append(server)
                except:
                    continue
            if (len(bestServers) == 0):
                printToConsole("[ERROR] Couldn't reach any nodes")
            else:
                server = random.choice(bestServers)
                targetBlock = bestCount + blockDelta
                txHex = subprocess.check_output([application_path + '/txgen', keyFile, toWallet, str(amount), str(fee), str(targetBlock)]).decode('utf8')
                rawTx = bytearray.fromhex(txHex)
                response = json.loads(requests.post(server + '/add_transaction', data=rawTx, headers={'Content-Type': 'application/octet-stream'}, timeout=2).text)

                if "status" in response and response["status"] == "SUCCESS":
                    printToConsole("[STATUS] Transaction received by node. Awaiting confirmation.")
                    while True:
                        try:
                            num = int(requests.get(server + "/block_count", timeout=DEFAULT_TIMEOUT).text)
                            time.sleep(1)
                            printToConsole("[STATUS] Current block: " + str(num) + ", tx target block: " + str(targetBlock))
                            if num >= targetBlock:
                                printToConsole("[STATUS] Reached tx target block, confirming")
                                response = json.loads(requests.post(server + '/verify_transaction', data=rawTx, headers={'Content-Type': 'application/octet-stream'}, timeout=2).text)
                                
                                if 'error' in response:
                                    printToConsole("[STATUS] Transaction was not confirmed. Retrying.")
                                    break
                                else:
                                    printToConsole("[STATUS] Transaction was confirmed.")
                                    return
                        except:
                            printToConsole("[ERROR] Could not fetch status from node.")
                else:
                    printToConsole("[ERROR] Transaction not accepted.")
                    printToConsole(response)
        printToConsole("[ERROR] All attempts failed")


    else:
        printToConsole("Unknown command")

file_checker = """
'.json' in user_input and 'privateKey' in open(user_input).read()
"""


@Gooey(program_name="PandaCoin Wallet", advanced=True, clear_before_run=True, richtext_controls=True, header_bg_color='#000000', default_size=(640,600), show_restart_button=False, show_success_modal=False, tabbed_groups=True, navigation='Tabbed',disable_stop_button=True, optional_cols=2) #@Gooey(optional_cols=2, program_name="PandaCoin Wallet")
def main():
    settings_msg = ''
    parser = GooeyParser(description=settings_msg)
    subs = parser.add_subparsers(help='commands', dest='command')

    
    create_key_parser = subs.add_parser(
        'Create-Wallet', help='Generates a new wallet')
    create_key_parser.add_argument(
        "Save Location", help="Location to store key file", widget="FileSaver", default="./keys.json", gooey_options={'default_file': 'keys.json'}) 
    
    # create_key_parser.add_argument(
    #     "Confirmation",  help="I understand that if I lose or delete the key file I will no longer have access to my funds. Type 'confirm-pandacoin-wallet' into the box below to confirm:", gooey_options={'full_width': True, 'validator':{ 'test': 'user_input=="confirm-pandacoin-wallet"', 'message': 'Please type "confirm-pandacoin-wallet" to confirm wallet creation'}})



    balance_parser = subs.add_parser(
        'Check-Balance', help='Get the current amount of coins held in an account')

    balance_parser.add_argument(
        "Wallet Address", help="Wallet address you want to check the balance of:", gooey_options = {'full_width': True, 'validator':{ 'test': 'len(user_input)==50 and user_input.isalnum()', 'message': 'Please enter a 50 digit HEX public wallet address'}})


    # ########################################################
    transfer_parser = subs.add_parser(
        'Send-Coins', help='Send coins to another wallet')
    transfer_parser.add_argument(
        "Your Key File", help="Location of wallet key file", widget="FileChooser", gooey_options={'validator': {'test':file_checker, 'message':'Invalid Key File'}})
    
    transfer_parser.add_argument(
        "Recepients Address", help="Wallet address you want to send coins to", gooey_options = {'full_width': True, 'validator':{ 'test': 'len(user_input)==50 and user_input.isalnum()', 'message': 'Please enter a 50 digit HEX public wallet address'}})

    transfer_parser.add_argument(
        "Amount"
    )

    transfer_parser.add_argument(
        "Fee"
    )

    # transfer_parser.add_argument(
    #     "Confirmation",  help="I understand that once I click start, I cannot revoke, edit, or cancel the transaction. Type 'confirm-pandacoin-send' into the box below to confirm:", gooey_options={'validator':{ 'test': 'user_input=="confirm-pandacoin-send"', 'message': 'Please type "confirm-pandacoin-send" to confirm transaction'}})

    transfer_parser.add_argument('-r', '--retries', default=2,  widget='IntegerField',
                                type=int, help='Number of times to retry submitting the transaction before giving up.\n(min=0, max=10)', gooey_options={'min': 0, 'max':10})
    
    transfer_parser.add_argument('-b', '--block_delta', default=1, widget='IntegerField',
                                type=int, help='The block delta specifies how many blocks in the future the transaction should be executed. A larger block delta increases the likelihood the transaction is accepted, but causes a longer execution time.\n (min=1, max=7)', gooey_options={'min': 1, 'max':7})

    parser.parse_args()

    display_message()


if __name__ == '__main__':
    main()

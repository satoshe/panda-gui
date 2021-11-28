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
from os.path import exists
import nacl.hash
import time
import random, string

def signTransaction(tx, privateKey):
    blockId = tx['id'].to_bytes(4, 'little') 
    signingKey = bytearray.fromhex(tx["signingKey"])
    timestamp = int(tx['timestamp']).to_bytes(8, 'little') 
    nonce = bytearray(tx['nonce'], encoding='utf8')
    toWallet = bytearray.fromhex(tx["to"])
    fromWallet = bytearray.fromhex(tx["from"])
    amount = tx["amount"].to_bytes(8, 'little') 
    fee = tx["fee"].to_bytes(8, 'little') 
    isFee = bytearray([0])    
    all_bytes = toWallet + fromWallet + fee + amount + nonce + blockId + timestamp
    hashed = nacl.hash.sha256(bytes(all_bytes))
    signature = privateKey.sign(hashed, encoder=HexEncoder)
    return str(signature, encoding='utf8').upper()

def createTransaction(blockId, pubKey, privKey, toAddr, fromAddr, amount, fee):
    transaction = {}
    transaction["id"] = blockId
    transaction["signingKey"] = str(pubKey.encode(encoder=HexEncoder), encoding='utf8').upper()
    transaction["timestamp"] = str(int(time.time()))
    transaction["to"] = toAddr
    transaction["from"] = fromAddr
    transaction["amount"] = amount
    transaction["fee"] = fee
    x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
    transaction["nonce"] = x
    transaction["signature"] = signTransaction(transaction, privKey)
    return transaction


def display_message():
    if sys.argv[1] == 'Check-Balance':
        to_check = sys.argv[3]
        print("Loading balance for " + to_check)
        servers = json.loads(requests.get('http://ec2-34-218-176-84.us-west-2.compute.amazonaws.com/hosts',timeout=3).text)
        for server in servers:
            try:
                balance = json.loads(requests.get(server + "/ledger/" + to_check, timeout=3).text)
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
            print("[ERROR] File : " + path + " already exists.")
        else:
            print("======GENERATING WALLET=======")
            time.sleep(1)
            output = subprocess.check_output(['./keygen', path])
            print(output)
            print("[SUCCESS] Key file : " + path + " saved")
    elif sys.argv[1] == 'Send-Coins':
        retries = int(sys.argv[3])
        blockDelta = int(sys.argv[5])
        keyFile = sys.argv[7]
        toWallet = sys.argv[8]
        amount = float(sys.argv[9])
        fee = float(sys.argv[10])
        for i in range(0, retries):
            print("[STATUS] Sending transaction (Attempt " + str(i+1) + ")")
            servers =  json.loads(requests.get('http://ec2-34-218-176-84.us-west-2.compute.amazonaws.com/hosts',timeout=3).text)
            bestCount = 0
            bestServers = []
            # fetch the best server
            for server in servers:
                # get block count:
                try:
                    num = int(requests.get(server + "/block_count", timeout=1).text)
                    if num > bestCount:
                        bestServers = [server]
                        bestCount = num
                    elif num == bestCount:
                        bestServers.append(server)
                except:
                    continue
            if (len(bestServers) == 0):
                print("[ERROR] Couldn't reach any nodes")
            else:
                server = random.choice(bestServers)
                targetBlock = bestCount + blockDelta
                txHex = subprocess.check_output(['./txgen', keyFile, toWallet, str(amount), str(fee), str(targetBlock)]).decode('utf8')
                rawTx = bytearray.fromhex(txHex)
                response = json.loads(requests.post(server + '/add_transaction', data=rawTx, headers={'Content-Type': 'application/octet-stream'}, timeout=2).text)

                if "status" in response and response["status"] == "SUCCESS":
                    print("[STATUS] Transaction received by node. Awaiting confirmation.")
                    while True:
                        num = int(requests.get(server + "/block_count", timeout=1).text)
                        time.sleep(1)
                        print("[STATUS] Current block: " + str(num) + ", tx target block: " + str(targetBlock))
                        if num >= targetBlock:
                            print("[STATUS] Reached tx target block, confirming")
                            response = json.loads(requests.post(server + '/verify_transaction', data=rawTx, headers={'Content-Type': 'application/octet-stream'}, timeout=2).text)
                            
                            if 'error' in response:
                                print("[STATUS] Transaction was not confirmed. Retrying.")
                                break
                            else:
                                print("[STATUS] Transaction was confirmed.")
                                return
                else:
                    print("[ERROR] Transaction not accepted.")
                    print(response)
        print("[ERROR] All attempts failed")


    else:
        print("Unknown command")

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

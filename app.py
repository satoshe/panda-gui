"""
Example program to demonstrate Gooey's presentation of subparsers
"""
import sys
import argparse
import time
import requests
from gooey import Gooey, GooeyParser
import json
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



def createWallet():
    # # Generate a new random signing key
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    verify_key_hex = verify_key.encode(encoder=HexEncoder)
    signing_key_hex = signing_key.encode(encoder=HexEncoder)
    pubKey = str(verify_key_hex, encoding='utf8').upper()
    privateKey = str(signing_key_hex, encoding='utf8').upper()
    hash = nacl.hash.sha256(bytes.fromhex(pubKey)).decode('utf8').upper()
    hash = bytearray.fromhex(hash)
    hash2 = hashlib.new('ripemd160', hash).hexdigest().upper()
    hash2 = bytes.fromhex(hash2)
    hash3 = nacl.hash.sha256(hash2).decode('utf8').upper()
    hash4 = nacl.hash.sha256(bytes.fromhex(hash3)).decode('utf8').upper()
    h2 = hash2
    h4 = bytes.fromhex(hash4)
    checksum = h4[0]

    address = bytearray(25*[0])
    address[0] = 0

    for i in range(1,21):
        address[i] = h2[i-1]
    address[21] = h4[0]
    address[22] = h4[1]
    address[23] = h4[2]
    address[24] = h4[3]
    wallet = address.hex().upper()
    ret = {
        "wallet": wallet,
        "privateKey": privateKey,
        "publicKey": pubKey
    }
    return ret


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
            data = createWallet()
            f = open(path, 'w')
            f.write(json.dumps(data, indent=4))
            print("[SUCCESS] Key file : " + path + " saved")
            print("New wallet address is : " + data["wallet"])
    elif sys.argv[1] == 'Send-Coins':
        retries = int(sys.argv[3])
        blockDelta = int(sys.argv[5])
        keyFile = sys.argv[7]
        toWallet = sys.argv[8]
        amount = int(sys.argv[9])*10000
        fee = int(sys.argv[10])*10000
        print("======GENERATING TRANSACTION=======")
        print(">to = " + toWallet)
        print(">keyFile = " + keyFile)
        print(">amount = " + str(amount))
        print(">fee = " + str(fee))
        print(">retries = " + str(retries))
        print(">blockDelta = " + str(blockDelta))
        for i in range(0, retries):
            print("======GETTING CHAIN HOST=======")
            servers =  ["http://localhost:3000"] #json.loads(requests.get('http://ec2-34-218-176-84.us-west-2.compute.amazonaws.com/hosts',timeout=3).text)
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
                print("[ERROR] COULD NOT CONNECT TO ANY NODE")
            else:
                server = random.choice(bestServers)
                targetBlock = bestCount + blockDelta
                # load key files
                wallet = json.loads(open(keyFile).read())
                fromWallet = wallet["wallet"]
                privKey = SigningKey(wallet["privateKey"], encoder=HexEncoder)
                pubKey = VerifyKey(wallet["publicKey"], encoder=HexEncoder)
                tx = createTransaction(targetBlock, pubKey, privKey, toWallet, fromWallet, amount, fee)
                print("===== TRANSACTION CREATED ======")
                print(json.dumps(tx, indent=4))
                response = json.loads(requests.post(server + '/add_transaction_json', json=tx, timeout=2).text)
                print("===== TRANSACTION SENT =======")
                print(response)
                if "status" in response and response["status"] == "SUCCESS":
                    print("===== TRANSACTION ACCEPTED, WAITING FOR TARGET BLOCK=======")
                    while True:
                        num = int(requests.get(server + "/block_count", timeout=1).text)
                        time.sleep(1)
                        print("Current block: " + str(num) + " tx target block: " + str(targetBlock))
                        if num >= targetBlock:
                            print("===== GOT TO TARGET BLOCK, CHECKING STATUS ======")
                            response = json.loads(requests.post(server + '/verify_transaction_json', json=tx, timeout=2).text)
                            print(response)
                            if 'error' in response:
                                print("===== TRANSACTION NOT IN TARGET BLOCK, RETRYING ======")
                                break
                            else:
                                print("===== TRANSACTION SUCCESSFUL ======")
                                return
                else:
                    print("===== TRANSACTION NOT ACCEPTED =======")
        print("===== ALL RETRIES FINISHED, TRANSACTION FAILED ======")


    else:
        print("Unknown command")

file_checker = """
'.json' in user_input and 'privateKey' in open(user_input).read()
"""


@Gooey(program_name="PandaCoin Wallet", advanced=True, clear_before_run=True, richtext_controls=True, header_bg_color='#000000', default_size=(640,700), show_restart_button=False, show_success_modal=False, tabbed_groups=True, navigation='Tabbed',disable_stop_button=True, optional_cols=2) #@Gooey(optional_cols=2, program_name="PandaCoin Wallet")
def main():
    settings_msg = ''
    parser = GooeyParser(description=settings_msg)
    subs = parser.add_subparsers(help='commands', dest='command')

    
    create_key_parser = subs.add_parser(
        'Create-Wallet', help='Generates a new wallet')
    create_key_parser.add_argument(
        "Save Location", help="Location to store key file", widget="FileSaver", default="./keys.json", gooey_options={'default_file': 'keys.json'}) 
    
    create_key_parser.add_argument(
        "Confirmation",  help="I understand that if I lose or delete the key file I will no longer have access to my funds. Type 'confirm-pandacoin-wallet' into the box below to confirm:", gooey_options={'full_width': True, 'validator':{ 'test': 'user_input=="confirm-pandacoin-wallet"', 'message': 'Please type "confirm-pandacoin-wallet" to confirm wallet creation'}})



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

    transfer_parser.add_argument(
        "Confirmation",  help="I understand that once I click start, I cannot revoke, edit, or cancel the transaction. Type 'confirm-pandacoin-send' into the box below to confirm:", gooey_options={'validator':{ 'test': 'user_input=="confirm-pandacoin-send"', 'message': 'Please type "confirm-pandacoin-send" to confirm transaction'}})

    transfer_parser.add_argument('-r', '--retries', default=2,  widget='IntegerField',
                                type=int, help='Number of times to retry submitting the transaction before giving up.\n(min=0, max=10)', gooey_options={'min': 0, 'max':10})
    
    transfer_parser.add_argument('-b', '--block_delta', default=2, widget='IntegerField',
                                type=int, help='The block delta specifies how many blocks in the future the transaction should be executed. A larger block delta increases the likelihood the transaction is accepted, but causes a longer execution time.\n (min=1, max=7)', gooey_options={'min': 1, 'max':7})

    parser.parse_args()

    display_message()


if __name__ == '__main__':
    main()

"""
Example program to demonstrate Gooey's presentation of subparsers
"""
import sys
import argparse
import time
from gooey import Gooey, GooeyParser

running = True


def display_message():
    print("FOO")
    print(sys.argv)
    time.sleep(3)

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
        "Save Location", help="Location to store keys.json file", widget="FileChooser", gooey_options={'validator': {'test':file_checker, 'message':'Invalid Key File'}})
    
    create_key_parser.add_argument(
        "Confirmation",  help="I understand that if I lose or delete the keys.json file I will no longer have access to my funds. Type 'confirm-pandacoin-wallet' into the box below to confirm:", gooey_options={'full_width': True, 'validator':{ 'test': 'user_input=="confirm-pandacoin-wallet"', 'message': 'Please type "confirm-pandacoin-wallet" to confirm wallet creation'}})



    balance_parser = subs.add_parser(
        'Check-Balance', help='Get the current amount of coins held in an account')

    balance_parser.add_argument(
        "Wallet Address", help="Wallet address you want to check the balance of:", gooey_options = {'full_width': True, 'validator':{ 'test': 'len(user_input)==50 and user_input.isalnum()', 'message': 'Please enter a 50 digit HEX public wallet address'}})


    # ########################################################
    transfer_parser = subs.add_parser(
        'Send-Coins', help='Send coins to another wallet')
    transfer_parser.add_argument(
        "Your Key File", help="Location of keys.json file", widget="FileChooser", gooey_options={'validator': {'test':file_checker, 'message':'Invalid Key File'}})
    
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

    transfer_parser.add_argument('-r', '--retries', default=0,  widget='IntegerField',
                                type=int, help='Number of times to retry submitting the transaction before giving up.\n(min=0, max=10)', gooey_options={'min': 0, 'max':10})
    
    transfer_parser.add_argument('-b', '--block_delta', default=2, widget='IntegerField',
                                type=int, help='The block delta specifies how many blocks in the future the transaction should be executed. A larger block delta increases the likelihood the transaction is accepted, but causes a longer confirmation time.\n (min=1, max=7)', gooey_options={'min': 1, 'max':7})

    parser.parse_args()

    display_message()


if __name__ == '__main__':
    main()

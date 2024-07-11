# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': '',
    "author": "",
    'description': '',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}
def run(protocol: protocol_api.ProtocolContext):
     # labware
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')

     # pipettes
    left_pipette = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])

     # loaction definitions

     # commands

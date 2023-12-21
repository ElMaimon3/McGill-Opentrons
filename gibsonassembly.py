# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Gibson Assembly',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}
def run(protocol: protocol_api.ProtocolContext):
    a = 1 #placeholder
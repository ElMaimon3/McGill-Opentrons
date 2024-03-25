from opentrons import protocol_api

metadata = {
    'protocolName': 'Volume to depth testing',
    'author': 'Your Name',
    'description': '''''',
    'apiLevel': '2.15'
}

# Protocol function
def run(protocol: protocol_api.ProtocolContext):
     # Load labware
    tube_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '2')
    # SETTINGS MUST BE ADJUSTED FOR EACH RUN
    # Define available reagents (mL):
    available_lysis = 15.0

    # Define reagent locations
    take_from = tube_rack['C5']
    put_in = tube_rack['B5']
    
    # Load pipettes
    p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '10')])
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[protocol.load_labware('opentrons_96_tiprack_20ul', '8')])
    p300.pick_up_tip()
    for i in range((15000-2000)//300):
        p300.transfer(300,take_from.top(-vol_to_height(available_lysis)),put_in, new_tip='never')
        available_lysis-=0.3
    p300.drop_tip()

def vol_to_height(vol):
    if vol < 2:
        raise ValueError('One of the buffers or washes is too low! Please add more')
    return round(-7.39231*vol + 111.885)